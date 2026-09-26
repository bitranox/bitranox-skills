#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx2"]
# ///
"""
AI-powered scientific schematic generation using Nano Banana 2.

This script uses a smart iterative refinement approach:
1. Generate initial image with Nano Banana 2
2. AI quality review using Gemini 3.1 Pro Preview for scientific critique
3. Only regenerate if quality is below threshold for document type
4. Repeat until quality meets standards (max iterations)

Requirements:
    - OPENROUTER_API_KEY environment variable (the only key source: a key on the command
      line would sit in the process list for the whole run)
    - httpx2 library

Exit status: 0 an image was written, reviewed and met the quality threshold; 1 no image, an
image whose review failed so its quality was NOT verified (only when no earlier image was
reviewed: otherwise the best-scoring reviewed image is kept and judged), or an image whose best
score stayed below the threshold (in both of those cases the image is still written); 2 a usage
error. The threshold is numeric: a kept image scoring at or above it exits 0 even when the
reviewer's verdict said NEEDS_IMPROVEMENT.

Usage:
    python generate_schematic_ai.py "Create a flowchart showing CONSORT participant flow" -o flowchart.png
    python generate_schematic_ai.py "Neural network architecture diagram" -o architecture.png --iterations 2
    python generate_schematic_ai.py "Simple block diagram" -o diagram.png --doc-type poster
"""

import argparse
import base64
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

try:
    import httpx2 as httpx
except ImportError:
    print("Error: httpx2 library not found. Run via: uv run --with httpx2 generate_schematic_ai.py",
          file=sys.stderr)
    sys.exit(1)

def _configure_console() -> None:
    """Replace unencodable characters instead of crashing on a narrow console (cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


# A "score" label, markup allowed between it and the number ("**SCORE:** 9.5", "Score - 9.5"),
# but not a line break, with an optional "/N" denominator.
_SCORE_LABEL = re.compile(
    r'\b(?P<label>(?:total|overall|final)\s+score|score)\b[^\w\n]*'
    r'(?P<num>\d+(?:\.\d+)?)(?:\s*\**\s*/\s*(?P<den>\d+(?:\.\d+)?))?',
    re.IGNORECASE,
)
# The older wording a review may use instead: "Rating: 7", "Overall quality: 6 / 10".
_FALLBACK_LABEL = re.compile(
    r'(?:rating|quality)[:\s]+(?P<num>\d+(?:\.\d+)?)(?:\s*/\s*(?P<den>\d+(?:\.\d+)?))?',
    re.IGNORECASE,
)
# What may stand before the label on its own line: indentation, emphasis, heading, quote.
_LINE_START_MARKUP = re.compile(r'[\s*_#>]*')


def _score_rank(content: str, match: "re.Match[str]") -> Tuple[int, int, int]:
    """Lower sorts first: how closely one candidate matches the requested "SCORE: <total>" line."""
    line_prefix = content[content.rfind("\n", 0, match.start()) + 1:match.start()]
    at_line_start = _LINE_START_MARKUP.fullmatch(line_prefix) is not None
    label = match.group("label")
    return (
        0 if label.split()[-1] == "SCORE" else 1,
        0 if at_line_start else 1,
        0 if label.lower() != "score" else 1,
    )


def _parse_score(content: str) -> Optional[float]:
    """The review's total score out of 10, or None when the review states none.

    The review prompt grades five criteria 0-2 each and then asks for "SCORE: [total score
    0-10]", so a review can carry several "score" labels. A candidate out of anything but 10
    ("Accuracy score (2/2)") or above 10 is a criterion, never the total. Of the rest, the one
    closest to the requested format wins: the upper-case SCORE label first, then a label that
    opens its line, then an explicit "total/overall/final score"; ties go to the first. With
    no "score" label at all, the first "rating"/"quality" value out of 10 is read, under the
    same out-of-10 rule ("quality: 2/2" is a criterion, not 2 out of 10).
    """
    candidates = []
    for match in _SCORE_LABEL.finditer(content):
        value = float(match.group("num"))
        denominator = match.group("den")
        if value > 10 or (denominator is not None and float(denominator) != 10):
            continue
        candidates.append((_score_rank(content, match), match.start(), value))
    if candidates:
        return min(candidates)[2]
    # The older "rating"/"quality" wording, under the same rule: the first one out of 10.
    for match in _FALLBACK_LABEL.finditer(content):
        value = float(match.group("num"))
        denominator = match.group("den")
        if value <= 10 and (denominator is None or float(denominator) == 10):
            return value
    return None


class ScientificSchematicGenerator:
    """Generate scientific schematics using AI with smart iterative refinement.
    
    Uses Gemini 3.1 Pro Preview for quality review to determine if regeneration is needed.
    Multiple passes only occur if the generated schematic doesn't meet the
    quality threshold for the target document type.
    """
    
    # Quality thresholds by document type (score out of 10)
    # Higher thresholds for more formal publications
    QUALITY_THRESHOLDS = {
        "journal": 8.5,      # Nature, Science, etc. - highest standards
        "conference": 8.0,   # Conference papers - high standards
        "poster": 7.0,       # Academic posters - good quality
        "presentation": 6.5, # Slides/talks - clear but less formal
        "report": 7.5,       # Technical reports - professional
        "grant": 8.0,        # Grant proposals - must be compelling
        "thesis": 8.0,       # Dissertations - formal academic
        "preprint": 7.5,     # arXiv, etc. - good quality
        "default": 7.5,      # Default threshold
    }
    
    # Scientific diagram best practices prompt template
    SCIENTIFIC_DIAGRAM_GUIDELINES = """
Create a high-quality scientific diagram with these requirements:

VISUAL QUALITY:
- Clean white or light background (no textures or gradients)
- High contrast for readability and printing
- Professional, publication-ready appearance
- Sharp, clear lines and text
- Adequate spacing between elements to prevent crowding

TYPOGRAPHY:
- Clear, readable sans-serif fonts (Arial, Helvetica style)
- Minimum 10pt font size for all labels
- Consistent font sizes throughout
- All text horizontal or clearly readable
- No overlapping text

SCIENTIFIC STANDARDS:
- Accurate representation of concepts
- Clear labels for all components
- Include scale bars, legends, or axes where appropriate
- Use standard scientific notation and symbols
- Include units where applicable

ACCESSIBILITY:
- Colorblind-friendly color palette (use Okabe-Ito colors if using color)
- High contrast between elements
- Redundant encoding (shapes + colors, not just colors)
- Works well in grayscale

LAYOUT:
- Logical flow (left-to-right or top-to-bottom)
- Clear visual hierarchy
- Balanced composition
- Appropriate use of whitespace
- No clutter or unnecessary decorative elements

IMPORTANT - NO FIGURE NUMBERS:
- Do NOT include "Figure 1:", "Fig. 1", or any figure numbering in the image
- Do NOT add captions or titles like "Figure: ..." at the top or bottom
- Figure numbers and captions are added separately in the document/LaTeX
- The diagram should contain only the visual content itself
"""
    
    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        """
        Initialize the generator.
        
        Args:
            api_key: OpenRouter API key (default: the OPENROUTER_API_KEY env var)
            verbose: Print detailed progress information
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not found. Set the OPENROUTER_API_KEY environment variable "
                "(or pass api_key to the constructor).\n"
                "Get your API key from: https://openrouter.ai/keys"
            )
        
        self.verbose = verbose
        self._last_error = None  # Track last error for better reporting
        self.base_url = "https://openrouter.ai/api/v1"
        # Both IDs are preview-tier, which providers rename and retire without notice.
        # Verified present in the live OpenRouter catalogue on 2026-08-28. When a run starts
        # failing with an opaque HTTP error, list the current IDs before debugging anything else:
        #   curl -s https://openrouter.ai/api/v1/models | python3 -c \
        #     "import json,sys; [print(m['id']) for m in json.load(sys.stdin)['data']]"
        # Nano Banana 2 - Google's advanced image generation model
        # https://openrouter.ai/google/gemini-3.1-flash-image-preview
        self.image_model = "google/gemini-3.1-flash-image-preview"
        # Gemini 3.1 Pro Preview for quality review - excellent vision and reasoning
        self.review_model = "google/gemini-3.1-pro-preview"
        
    def _log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def _make_request(self, model: str, messages: List[Dict[str, Any]], 
                     modalities: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Make a request to OpenRouter API.
        
        Args:
            model: Model identifier
            messages: List of message dictionaries
            modalities: Optional list of modalities (e.g., ["image", "text"])
            
        Returns:
            API response as dictionary
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/scientific-writer",
            "X-Title": "Scientific Schematic Generator"
        }
        
        payload = {
            "model": model,
            "messages": messages
        }
        
        if modalities:
            payload["modalities"] = modalities
        
        self._log(f"Making request to {model}...")
        
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            # Try to get response body even on error
            try:
                response_json = response.json()
            except json.JSONDecodeError:
                response_json = {"raw_text": response.text[:500]}
            
            # Check for HTTP errors but include response body in error message
            if response.status_code != 200:
                error_detail = response_json.get("error", response_json)
                self._log(f"HTTP {response.status_code}: {error_detail}")
                raise RuntimeError(f"API request failed (HTTP {response.status_code}): {error_detail}")
            
            return response_json
        except httpx.TimeoutException:
            raise RuntimeError("API request timed out after 120 seconds")
        except httpx.RequestError as e:
            raise RuntimeError(f"API request failed: {str(e)}")
    
    def _extract_image_from_response(self, response: Dict[str, Any]) -> Optional[bytes]:
        """
        Extract base64-encoded image from API response.
        
        For Nano Banana 2, images are returned in the 'images' field of the message,
        not in the 'content' field.
        
        Args:
            response: API response dictionary
            
        Returns:
            Image bytes or None if not found
        """
        try:
            choices = response.get("choices", [])
            if not choices:
                self._log("No choices in response")
                return None
            
            message = choices[0].get("message", {})
            
            # IMPORTANT: Nano Banana 2 returns images in the 'images' field
            images = message.get("images", [])
            if images and len(images) > 0:
                self._log(f"Found {len(images)} image(s) in 'images' field")
                
                # Get first image
                first_image = images[0]
                if isinstance(first_image, dict):
                    # Extract image_url
                    if first_image.get("type") == "image_url":
                        url = first_image.get("image_url", {})
                        if isinstance(url, dict):
                            url = url.get("url", "")
                        
                        if url and url.startswith("data:image"):
                            # Extract base64 data after comma
                            if "," in url:
                                base64_str = url.split(",", 1)[1]
                                # Clean whitespace
                                base64_str = base64_str.replace('\n', '').replace('\r', '').replace(' ', '')
                                self._log(f"Extracted base64 data (length: {len(base64_str)})")
                                return base64.b64decode(base64_str)
            
            # Fallback: check content field (for other models or future changes)
            content = message.get("content", "")
            
            if self.verbose:
                self._log(f"Content type: {type(content)}, length: {len(str(content))}")
            
            # Handle string content
            if isinstance(content, str) and "data:image" in content:
                import re
                match = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=\n\r]+)', content, re.DOTALL)
                if match:
                    base64_str = match.group(1).replace('\n', '').replace('\r', '').replace(' ', '')
                    self._log(f"Found image in content field (length: {len(base64_str)})")
                    return base64.b64decode(base64_str)
            
            # Handle list content
            if isinstance(content, list):
                for i, block in enumerate(content):
                    if isinstance(block, dict) and block.get("type") == "image_url":
                        url = block.get("image_url", {})
                        if isinstance(url, dict):
                            url = url.get("url", "")
                        if url and url.startswith("data:image") and "," in url:
                            base64_str = url.split(",", 1)[1].replace('\n', '').replace('\r', '').replace(' ', '')
                            self._log(f"Found image in content block {i}")
                            return base64.b64decode(base64_str)
            
            self._log("No image data found in response")
            return None
            
        except Exception as e:
            self._log(f"Error extracting image: {str(e)}")
            import traceback
            if self.verbose:
                traceback.print_exc()
            return None
    
    def _image_to_base64(self, image_path: str) -> str:
        """
        Convert image file to base64 data URL.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 data URL string
        """
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # Determine image type from extension
        ext = Path(image_path).suffix.lower()
        mime_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }.get(ext, "image/png")
        
        base64_data = base64.b64encode(image_data).decode("utf-8")
        return f"data:{mime_type};base64,{base64_data}"
    
    def generate_image(self, prompt: str) -> Optional[bytes]:
        """
        Generate an image using Nano Banana 2.
        
        Args:
            prompt: Description of the diagram to generate
            
        Returns:
            Image bytes or None if generation failed
        """
        self._last_error = None  # Reset error
        
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = self._make_request(
                model=self.image_model,
                messages=messages,
                modalities=["image", "text"]
            )
            
            # Debug: print response structure if verbose
            if self.verbose:
                self._log(f"Response keys: {response.keys()}")
                if "error" in response:
                    self._log(f"API Error: {response['error']}")
                if "choices" in response and response["choices"]:
                    msg = response["choices"][0].get("message", {})
                    self._log(f"Message keys: {msg.keys()}")
                    # Show content preview without printing huge base64 data
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        preview = content[:200] + "..." if len(content) > 200 else content
                        self._log(f"Content preview: {preview}")
                    elif isinstance(content, list):
                        self._log(f"Content is list with {len(content)} items")
                        for i, item in enumerate(content[:3]):
                            if isinstance(item, dict):
                                self._log(f"  Item {i}: type={item.get('type')}")
            
            # Check for API errors in response
            if "error" in response:
                error_msg = response["error"]
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get("message", str(error_msg))
                self._last_error = f"API Error: {error_msg}"
                print(f"[FAIL] {self._last_error}")
                return None
            
            image_data = self._extract_image_from_response(response)
            if image_data:
                self._log(f"[OK] Generated image ({len(image_data)} bytes)")
            else:
                self._last_error = "No image data in API response - model may not support image generation"
                self._log(f"[FAIL] {self._last_error}")
                # Additional debug info when image extraction fails
                if self.verbose and "choices" in response:
                    msg = response["choices"][0].get("message", {})
                    self._log(f"Full message structure: {json.dumps({k: type(v).__name__ for k, v in msg.items()})}")
            
            return image_data
        except RuntimeError as e:
            self._last_error = str(e)
            self._log(f"[FAIL] Generation failed: {self._last_error}")
            return None
        except Exception as e:
            self._last_error = f"Unexpected error: {str(e)}"
            self._log(f"[FAIL] Generation failed: {self._last_error}")
            import traceback
            if self.verbose:
                traceback.print_exc()
            return None
    
    def review_image(self, image_path: str, original_prompt: str, 
                    iteration: int, doc_type: str = "default",
                    max_iterations: int = 2) -> Tuple[str, float, bool]:
        """
        Review generated image using Gemini 3.1 Pro Preview for quality analysis.
        
        Uses Gemini 3.1 Pro Preview's superior vision and reasoning capabilities to
        evaluate the schematic quality and determine if regeneration is needed.
        
        Args:
            image_path: Path to the generated image
            original_prompt: Original user prompt
            iteration: Current iteration number
            doc_type: Document type (journal, poster, presentation, etc.)
            max_iterations: Maximum iterations allowed
            
        Returns:
            Tuple of (critique text, quality score 0-10, needs_improvement bool). The score
            is None when no score could be established - the request failed, the response
            had no choices, or the review stated no score. The critique then says why, and
            needs_improvement is False: there is no critique to regenerate from.
        """
        # Use Gemini 3.1 Pro Preview for review - excellent vision and analysis
        image_data_url = self._image_to_base64(image_path)
        
        # Get quality threshold for this document type
        threshold = self.QUALITY_THRESHOLDS.get(doc_type.lower(), 
                                                 self.QUALITY_THRESHOLDS["default"])
        
        review_prompt = f"""You are an expert reviewer evaluating a scientific diagram for publication quality.

ORIGINAL REQUEST: {original_prompt}

DOCUMENT TYPE: {doc_type} (quality threshold: {threshold}/10)
ITERATION: {iteration}/{max_iterations}

Carefully evaluate this diagram on these criteria:

1. **Scientific Accuracy** (0-2 points)
   - Correct representation of concepts
   - Proper notation and symbols
   - Accurate relationships shown

2. **Clarity and Readability** (0-2 points)
   - Easy to understand at a glance
   - Clear visual hierarchy
   - No ambiguous elements

3. **Label Quality** (0-2 points)
   - All important elements labeled
   - Labels are readable (appropriate font size)
   - Consistent labeling style

4. **Layout and Composition** (0-2 points)
   - Logical flow (top-to-bottom or left-to-right)
   - Balanced use of space
   - No overlapping elements

5. **Professional Appearance** (0-2 points)
   - Publication-ready quality
   - Clean, crisp lines and shapes
   - Appropriate colors/contrast

RESPOND IN THIS EXACT FORMAT:
SCORE: [total score 0-10]

STRENGTHS:
- [strength 1]
- [strength 2]

ISSUES:
- [issue 1 if any]
- [issue 2 if any]

VERDICT: [ACCEPTABLE or NEEDS_IMPROVEMENT]

If score >= {threshold}, the diagram is ACCEPTABLE for {doc_type} publication.
If score < {threshold}, mark as NEEDS_IMPROVEMENT with specific suggestions."""

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": review_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        }
                    }
                ]
            }
        ]
        
        try:
            # Use Gemini 3.1 Pro Preview for high-quality review
            response = self._make_request(
                model=self.review_model,
                messages=messages
            )
            
            # Extract text response
            choices = response.get("choices", [])
            if not choices:
                return "Review skipped: the review response had no choices", None, False
            
            message = choices[0].get("message", {})
            content = message.get("content", "")
            
            # Check reasoning field (Nano Banana 2 puts analysis here)
            reasoning = message.get("reasoning", "")
            if reasoning and not content:
                content = reasoning
            
            if isinstance(content, list):
                # Extract text from content blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                content = "\n".join(text_parts)
            
            score = _parse_score(content or "")
            if score is None:
                return "Review skipped: the review stated no score\n" + (content or ""), None, False
            
            # Determine if improvement is needed based on verdict or score
            needs_improvement = "NEEDS_IMPROVEMENT" in content.upper() or score < threshold
            
            self._log(f"[OK] Review complete (Score: {score}/10, Threshold: {threshold}/10)")
            self._log(f"  Verdict: {'Needs improvement' if needs_improvement else 'Acceptable'}")
            
            return (content if content else "Image generated successfully", 
                    score, 
                    needs_improvement)
        except Exception as e:
            self._log(f"Review skipped: {str(e)}")
            # A failed review does not fail the run, but it proves nothing about quality.
            return f"Review skipped: {str(e)}", None, False
    
    def improve_prompt(self, original_prompt: str, critique: str, 
                      iteration: int) -> str:
        """
        Improve the generation prompt based on critique.
        
        Args:
            original_prompt: Original user prompt
            critique: Review critique from previous iteration
            iteration: Current iteration number
            
        Returns:
            Improved prompt for next generation
        """
        improved_prompt = f"""{self.SCIENTIFIC_DIAGRAM_GUIDELINES}

USER REQUEST: {original_prompt}

ITERATION {iteration}: Based on previous feedback, address these specific improvements:
{critique}

Generate an improved version that addresses all the critique points while maintaining scientific accuracy and professional quality."""
        
        return improved_prompt
    
    def generate_iterative(self, user_prompt: str, output_path: str,
                          iterations: int = 2, 
                          doc_type: str = "default") -> Dict[str, Any]:
        """
        Generate scientific schematic with smart iterative refinement.
        
        Only regenerates if the quality score is below the threshold for the
        specified document type. This saves API calls and time when the first
        generation is already good enough.
        
        Args:
            user_prompt: User's description of desired diagram
            output_path: Path to save final image
            iterations: Maximum refinement iterations (default: 2, max: 2)
            doc_type: Document type for quality threshold (journal, poster, etc.)
            
        Returns:
            Dictionary with generation results and metadata
        """
        output_path = Path(output_path)
        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        base_name = output_path.stem
        extension = output_path.suffix or ".png"
        
        # Get quality threshold for this document type
        threshold = self.QUALITY_THRESHOLDS.get(doc_type.lower(), 
                                                 self.QUALITY_THRESHOLDS["default"])
        
        results = {
            "user_prompt": user_prompt,
            "doc_type": doc_type,
            "quality_threshold": threshold,
            "iterations": [],
            "final_image": None,
            "final_score": 0.0,
            "success": False,
            "early_stop": False,
            "early_stop_reason": None,
            "review_skipped": False,
            # True when the delivered image scored at or above the threshold, False when it
            # scored below it, None when no score was established (the review failed).
            "threshold_met": False
        }
        
        current_prompt = f"""{self.SCIENTIFIC_DIAGRAM_GUIDELINES}

USER REQUEST: {user_prompt}

Generate a publication-quality scientific diagram that meets all the guidelines above."""
        
        print(f"\n{'='*60}")
        print("Generating Scientific Schematic")
        print(f"{'='*60}")
        print(f"Description: {user_prompt}")
        print(f"Document Type: {doc_type}")
        print(f"Quality Threshold: {threshold}/10")
        print(f"Max Iterations: {iterations}")
        print(f"Output: {output_path}")
        print(f"{'='*60}\n")
        
        # The highest-scoring reviewed image so far: kept when a later generation fails,
        # so a paid, reviewed image is never thrown away for a retry that produced nothing.
        best = None
        for i in range(1, iterations + 1):
            print(f"\n[Iteration {i}/{iterations}]")
            print("-" * 40)

            # Generate image
            print("Generating image...")
            image_data = self.generate_image(current_prompt)

            if not image_data:
                error_msg = self._last_error or 'Image generation failed - no image data returned'
                print(f"[FAIL] Generation failed: {error_msg}")
                results["iterations"].append({
                    "iteration": i,
                    "success": False,
                    "error": error_msg
                })
                continue

            # Save iteration image
            iter_path = output_dir / f"{base_name}_v{i}{extension}"
            with open(iter_path, "wb") as f:
                f.write(image_data)
            print(f"[OK] Saved: {iter_path}")

            # Review image using Gemini 3.1 Pro Preview
            print("Reviewing image with Gemini 3.1 Pro Preview...")
            critique, score, needs_improvement = self.review_image(
                str(iter_path), user_prompt, i, doc_type, iterations
            )

            # Save iteration results
            iteration_result = {
                "iteration": i,
                "image_path": str(iter_path),
                "prompt": current_prompt,
                "critique": critique,
                "score": score,
                "needs_improvement": needs_improvement,
                "success": True
            }
            results["iterations"].append(iteration_result)

            if score is None:
                print(f"[WARN] {critique.splitlines()[0]}")
                if best is not None:
                    # An earlier image WAS reviewed. This one's quality is unknown, so it cannot
                    # outrank a known score: keep-best below chooses among reviewed images only.
                    results["unreviewed_iteration"] = i
                    break
                # No reviewed image at all: keep this one, but say plainly that its quality is
                # unknown.
                print(f"[WARN] Quality NOT verified against the {doc_type} threshold ({threshold}/10)")
                results["final_image"] = str(iter_path)
                results["final_score"] = None
                results["success"] = True
                results["review_skipped"] = True
                results["threshold_met"] = None
                break
            print(f"[OK] Score: {score}/10 (threshold: {threshold}/10)")
            if best is None or score > best["score"]:
                best = iteration_result

            # Check if quality is acceptable - STOP EARLY if so
            if not needs_improvement:
                print(f"\n[OK] Quality meets {doc_type} threshold ({score} >= {threshold})")
                print("  No further iterations needed!")
                results["final_image"] = str(iter_path)
                results["final_score"] = score
                results["success"] = True
                results["threshold_met"] = True
                results["early_stop"] = True
                results["early_stop_reason"] = f"Quality score {score} meets threshold {threshold} for {doc_type}"
                break

            # If this is the last iteration, we're done regardless. The image kept is chosen
            # below from every reviewed one: a retry can score WORSE than what it replaced.
            if i == iterations:
                print("\n[WARN] Maximum iterations reached")
                break

            # Quality below threshold - improve prompt for next iteration
            print(f"\n[WARN] Quality below threshold ({score} < {threshold})")
            print("Improving prompt based on feedback...")
            current_prompt = self.improve_prompt(user_prompt, critique, i + 1)

        if not results["success"] and best is not None:
            # No image met the threshold, the last generation failed, or the last image's review
            # failed: every reviewed image was paid for, so the one delivered is the
            # best-scoring REVIEWED one, never simply the last.
            last_failed = not results["iterations"][-1].get("success")
            unreviewed = results.get("unreviewed_iteration")
            # A score at or above the threshold lands here when the reviewer's verdict still
            # asked for improvement, so "below" is said only when it is true.
            met = best["score"] >= threshold
            if last_failed:
                reason = "The last generation failed"
            elif unreviewed is not None:
                reason = (f"The review of v{unreviewed} failed, so its quality is unknown "
                          f"(it stays on disk as {results['iterations'][-1]['image_path']})")
            else:
                reason = "No image was judged acceptable" if met else "No image met the threshold"
            relation = "at or above" if met else "below"
            print(f"\n[WARN] {reason}; keeping v{best['iteration']}, the best-scoring reviewed "
                  f"image (score {best['score']}/10, {relation} the {threshold}/10 threshold)")
            results["final_image"] = best["image_path"]
            results["final_score"] = best["score"]
            results["success"] = True
            results["threshold_met"] = met
            results["kept_iteration"] = best["iteration"]
            if last_failed or unreviewed is not None:
                results["fallback_iteration"] = best["iteration"]

        # Copy final version to output path
        if results["success"] and results["final_image"]:
            final_iter_path = Path(results["final_image"])
            if final_iter_path != output_path:
                shutil.copy(final_iter_path, output_path)
                print(f"\n[OK] Final image: {output_path}")

        # Save review log
        log_path = output_dir / f"{base_name}_review_log.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[OK] Review log: {log_path}")

        print(f"\n{'='*60}")
        print("Generation Complete!")
        final_score = results["final_score"]
        print(f"Final Score: {'not reviewed' if final_score is None else f'{final_score}/10'}")
        if results["early_stop"]:
            print(f"Iterations Used: {len([r for r in results['iterations'] if r.get('success')])}/{iterations} (early stop)")
        print(f"{'='*60}\n")

        return results


def build_parser() -> argparse.ArgumentParser:
    """The command-line parser (the wrapper script's tests parse its child argv with it)."""
    parser = argparse.ArgumentParser(
        description="Generate scientific schematics using AI with smart iterative refinement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a flowchart for a journal paper
  python generate_schematic_ai.py "CONSORT participant flow diagram" -o flowchart.png --doc-type journal
  
  # Generate neural network architecture for presentation (lower threshold)
  python generate_schematic_ai.py "Transformer encoder-decoder architecture" -o transformer.png --doc-type presentation
  
  # Generate with custom max iterations for poster
  python generate_schematic_ai.py "Biological signaling pathway" -o pathway.png --iterations 2 --doc-type poster
  
  # Verbose output
  python generate_schematic_ai.py "Circuit diagram" -o circuit.png -v

Document Types (quality thresholds):
  journal      8.5/10  - Nature, Science, peer-reviewed journals
  conference   8.0/10  - Conference papers
  thesis       8.0/10  - Dissertations, theses
  grant        8.0/10  - Grant proposals
  preprint     7.5/10  - arXiv, bioRxiv, etc.
  report       7.5/10  - Technical reports
  poster       7.0/10  - Academic posters
  presentation 6.5/10  - Slides, talks
  default      7.5/10  - General purpose

Note: Multiple iterations only occur if quality is BELOW the threshold.
      If the first generation meets the threshold, no extra API calls are made.

Environment:
  OPENROUTER_API_KEY    OpenRouter API key (required; the only way to pass the key)

Exit status: 0 image written, reviewed and at or above the threshold; 1 failure, review
unavailable with no earlier reviewed image, or best reviewed score below the threshold (the
image may still be written); 2 usage error. The threshold is numeric: a NEEDS_IMPROVEMENT
verdict on a score at or above it still exits 0.
        """
    )
    
    parser.add_argument("prompt", help="Description of the diagram to generate")
    parser.add_argument("-o", "--output", required=True, 
                       help="Output image path (e.g., diagram.png)")
    parser.add_argument("--iterations", type=int, default=2,
                       help="Maximum refinement iterations (default: 2, max: 2)")
    parser.add_argument("--doc-type", default="default",
                       choices=["journal", "conference", "poster", "presentation", 
                               "report", "grant", "thesis", "preprint", "default"],
                       help="Document type for quality threshold (default: default)")
    # Refused in main(), never used: the key comes from OPENROUTER_API_KEY only.
    parser.add_argument("--api-key", help=argparse.SUPPRESS)
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Verbose output")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Command-line interface."""
    _configure_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.api_key is not None:
        # Accepted by the parser only to refuse it with a reason; the value is never echoed.
        parser.error("--api-key is not accepted: a key on the command line is visible in the "
                     "process list for the whole run. Set OPENROUTER_API_KEY in the environment.")

    # Validate iterations - enforce max of 2. A usage error (exit 2), checked before the key so a
    # bad argument is named even where no key is set.
    if args.iterations < 1 or args.iterations > 2:
        parser.error("Iterations must be between 1 and 2")

    # Check for API key. Errors go to stderr: stdout carries the run's progress lines.
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set", file=sys.stderr)
        print("\nSet it with:", file=sys.stderr)
        print("  export OPENROUTER_API_KEY='your_api_key'", file=sys.stderr)
        return 1

    try:
        generator = ScientificSchematicGenerator(api_key=api_key, verbose=args.verbose)
        results = generator.generate_iterative(
            user_prompt=args.prompt,
            output_path=args.output,
            iterations=args.iterations,
            doc_type=args.doc_type
        )

        if not results["success"]:
            print("\n[FAIL] Generation failed. Check review log for details.")
            return 1
        if results.get("review_skipped"):
            print(f"\n[WARN] Image saved to {args.output}, but its quality was NOT verified "
                  f"(the review failed); exiting 1")
            return 1
        if results.get("threshold_met") is False:
            # User decision 2026-09-26: the best image is delivered, but a run that never met
            # the threshold is a "no" (exit 1), not a success.
            print(f"\n[WARN] Image saved to {args.output}, but it missed the {args.doc_type} "
                  f"quality threshold: best score {results['final_score']}/10 is below "
                  f"{results['quality_threshold']}/10; exiting 1")
            return 1
        print(f"\n[OK] Success! Image saved to: {args.output}")
        if results.get("early_stop"):
            print(f"  (Completed in {len([r for r in results['iterations'] if r.get('success')])} iteration(s) - quality threshold met)")
        return 0
    except Exception as e:
        print(f"\n[FAIL] Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
