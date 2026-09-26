"""find_cache_candidates: source decoding, the purity heuristic, and the CLI contract.

The CLI is driven as a subprocess, the way SKILL.md Step 4a runs it.
"""
import ast
import textwrap

import pytest

import find_cache_candidates as fcc

SCRIPT = "find_cache_candidates.py"
PURE_BODY = "def square_sum(n):\n    total = 0\n    for i in range(n):\n        total += i * i\n    return total\n"


def _names(path):
    return {c["function"] for c in fcc.find_cache_candidates(str(path))}


# --- decoding: a file python3 runs must be scannable --------------------------------------

def test_utf8_bom_file_is_scanned(tmp_path):
    p = tmp_path / "bom.py"
    p.write_bytes(b"\xef\xbb\xbf" + PURE_BODY.encode())
    assert _names(p) == {"square_sum"}


def test_pep263_latin1_file_is_scanned(tmp_path):
    p = tmp_path / "latin.py"
    p.write_bytes(b"# -*- coding: latin-1 -*-\n# caf\xe9\n" + PURE_BODY.encode())
    assert _names(p) == {"square_sum"}


def test_unparseable_file_raises_instead_of_returning_empty(tmp_path):
    p = tmp_path / "bad.py"
    p.write_text("def (oops:\n", encoding="utf-8")
    with pytest.raises(SyntaxError):
        fcc.find_cache_candidates(str(p))


# --- purity heuristic ------------------------------------------------------------------

IMPURE = textwrap.dedent('''
    import subprocess
    import time
    import datetime
    import functools
    from functools import lru_cache

    COUNT = 0

    def gen(n):
        for i in range(n):
            yield i * i

    def gen_from(n):
        for _ in range(n):
            pass
        yield from range(n)

    def fill(out, n):
        for i in range(n):
            out[i] = i

    def set_attr(obj, n):
        for i in range(n):
            obj.total = i

    def fetch(cmds):
        for c in cmds:
            subprocess.run(c)

    def stamp(n):
        for _ in range(n):
            pass
        return time.time()

    def clock(n):
        for _ in range(n):
            pass
        return time.perf_counter()

    def when(n):
        for _ in range(n):
            pass
        return datetime.datetime.now()

    def bump(n):
        global COUNT
        for _ in range(n):
            COUNT += 1

    def printer(n):
        for i in range(n):
            print(i)

    @functools.lru_cache(maxsize=None)
    def dotted_cached(n):
        for i in range(n):
            pass
        return n

    @functools.cache
    def dotted_cache(n):
        for i in range(n):
            pass
        return n

    def square_sum(n):
        total = 0
        for i in range(n):
            total += i * i
        return total
''')


def test_impure_functions_are_not_candidates(tmp_path):
    p = tmp_path / "gen.py"
    p.write_text(IMPURE, encoding="utf-8")
    assert _names(p) == {"square_sum"}


# A store into a container the function CREATED is invisible to every caller: DP tables and
# local tallies are the textbook lru_cache candidates. Each function below is pure.
LOCAL_STORES = textwrap.dedent('''
    import collections

    def lcs(a, b):
        n, m = len(a), len(b)
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp[n][m]

    def word_count(words):
        counts = {}
        for w in words:
            counts[w] = counts.get(w, 0) + 1
        return len(counts)

    def fib_table(n):
        table = [0] * (n + 2)
        table[1] = 1
        for i in range(2, n + 1):
            table[i] = table[i - 1] + table[i - 2]
        return table[n]

    def tally(xs):
        seen = dict()
        for x in xs:
            seen[x] = True
        del seen[xs[0]]
        return len(seen)

    def groups(xs):
        by_len = collections.defaultdict(list)
        for x in xs:
            by_len[len(x)] += [x]
        return len(by_len)

    def rolling(n):
        prev, cur = [0] * n, [0] * n
        for i in range(n):
            cur[i] = prev[i] + 1
        return cur[-1]

    def patched(base, n):
        d = dict(base)
        e = base.copy()
        for i in range(n):
            d[i] = i
            e[i] = i
        return len(d) + len(e)

    def squares(n):
        sq = {i: i * i for i in range(n)}
        for i in range(n):
            sq[i] += 1
        return sum(sq.values())

    def outer(n):
        memo = {}

        def helper(k):
            return k * 2
        for i in range(n):
            memo[i] = helper(i)
        return len(memo)

    def closure_owner(n):
        memo = {}

        def closure_writer(k):
            for _ in range(k):
                memo[k] = k
            return k
        return closure_writer(n)
''')

# The same shapes, but the store reaches an object the CALLER can see.
SHARED_STORES = textwrap.dedent('''
    CACHE = {}

    def into_param(out, n):
        for i in range(n):
            out[i] = i

    def into_global(n):
        for i in range(n):
            CACHE[i] = i

    def into_alias(param, n):
        d = param
        for i in range(n):
            d[i] = i

    def rebound(param, n):
        d = {}
        d = param
        for i in range(n):
            d[i] = i

    def into_row(grid):
        for row in grid:
            row[0] = 0

    def into_element(param, n):
        rows = [param]
        for i in range(n):
            rows[0][i] = i

    def unpacked(pair, n):
        a, b = pair
        for i in range(n):
            a[i] = i

    def walrus(param, n):
        if (d := param):
            for i in range(n):
                d[i] = i

    class K:
        def setter(self, n):
            for i in range(n):
                self.total = i

        def into_self_dict(self, n):
            for i in range(n):
                self.table[i] = i

    def param_closure_owner(memo, n):
        def param_closure_writer(k):
            for _ in range(k):
                memo[k] = k
            return k
        return param_closure_writer(n)

    def shadowed(target, n):
        memo = {}

        def writer(memo):
            for i in range(n):
                memo[i] = i
        writer(target)
        return len(memo)
''')


def test_stores_into_a_locally_created_container_keep_a_function_pure(tmp_path):
    p = tmp_path / "local.py"
    p.write_text(LOCAL_STORES, encoding="utf-8")
    # closure_owner's store happens in the nested closure_writer, into the owner's own memo:
    # the owner is pure, but closure_writer, seen on its own, writes into a closure and is not.
    assert _names(p) == {"lcs", "word_count", "fib_table", "tally", "groups", "rolling",
                         "patched", "squares", "outer", "closure_owner"}


def test_stores_that_reach_a_caller_visible_object_stay_impure(tmp_path):
    p = tmp_path / "shared.py"
    p.write_text(SHARED_STORES, encoding="utf-8")
    assert _names(p) == set()


def test_shared_store_fixture_is_expensive_so_only_purity_excludes_it(tmp_path):
    """Liveness for the control above: every function there has a loop, so an empty result
    can only come from the purity check, never from 'not expensive'."""
    funcs = [n for n in ast.walk(ast.parse(SHARED_STORES)) if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 14
    assert all(fcc.is_expensive_computation(f) for f in funcs)


# A mutating METHOD call follows the same rule as a subscript store: onto a container this
# function created it is invisible to every caller; onto anything else it is a side effect.
LOCAL_METHOD_MUTATIONS = textwrap.dedent('''
    import collections
    import numpy as np

    def collect(n):
        out = []
        for i in range(n):
            out.append(i * i)
        return sum(out)

    def seen_count(xs):
        s = set()
        for x in xs:
            s.add(x)
        s.discard(None)
        return len(s)

    def by_len(xs):
        groups = collections.defaultdict(list)
        for x in xs:
            groups[len(x)].append(x)
        return len(groups)

    def walk(start):
        stack, seen = [start], {}
        while stack:
            node = stack.pop()
            seen.setdefault(node, 0)
            seen.update({node: 1})
        return len(seen)

    def rows_extend(n):
        grid = [[] for _ in range(n)]
        for i in range(n):
            grid[i].extend([i])
            grid[i].insert(0, i)
        return len(grid)

    def sorted_local(xs):
        tmp = list(xs)
        for _ in range(3):
            tmp.sort()
            tmp.reverse()
        tmp.clear()
        return len(tmp)

    def np_table(n):
        t = np.zeros((n, n))
        for i in range(n):
            t[i, i] = 1
            t[i][0] = 2
        t.fill(0)
        return t.sum()
''')

PARAM_METHOD_MUTATIONS = textwrap.dedent('''
    RESULTS = []

    def ext(out, n):
        for i in range(n):
            out.extend([i])

    def ins(out, n):
        for i in range(n):
            out.insert(0, i)

    def upd(d, n):
        for i in range(n):
            d.update({i: i})

    def add(s, n):
        for i in range(n):
            s.add(i)

    def popper(xs, n):
        for _ in range(n):
            xs.pop()

    def sorter(xs, n):
        for _ in range(n):
            pass
        xs.sort()

    def clr(xs, n):
        for _ in range(n):
            pass
        xs.clear()

    def sd(d, n):
        for i in range(n):
            d.setdefault(i, [])

    def rm(xs, n):
        for i in range(n):
            xs.remove(i)

    def disc(s, n):
        for i in range(n):
            s.discard(i)

    def glob_append(n):
        for i in range(n):
            RESULTS.append(i)

    def alias_append(p, n):
        q = p
        for i in range(n):
            q.append(i)

    def row_append(grid):
        for row in grid:
            row.append(0)

    def element_of_local(param, n):
        rows = [param]
        for i in range(n):
            rows[0].append(i)

    class K:
        def self_append(self, n):
            for i in range(n):
                self.items.append(i)
''')


def test_mutating_methods_on_a_locally_created_container_keep_a_function_pure(tmp_path):
    p = tmp_path / "local_methods.py"
    p.write_text(LOCAL_METHOD_MUTATIONS, encoding="utf-8")
    assert _names(p) == {"collect", "seen_count", "by_len", "walk", "rows_extend",
                         "sorted_local", "np_table"}


def test_mutating_methods_on_a_caller_visible_object_make_a_function_impure(tmp_path):
    p = tmp_path / "param_methods.py"
    p.write_text(PARAM_METHOD_MUTATIONS, encoding="utf-8")
    funcs = [n for n in ast.walk(ast.parse(PARAM_METHOD_MUTATIONS)) if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 15 and all(fcc.is_expensive_computation(f) for f in funcs)  # liveness
    assert _names(p) == set()


# lru_cache hands every caller the SAME returned object, so a function that returns a mutable
# container it built is not a safe candidate: one caller's edit changes every later result.
RETURNS_MUTABLE = textwrap.dedent('''
    import numpy as np

    def squares_list(n):
        out = []
        for i in range(n):
            out.append(i * i)
        return out

    def table(n):
        for _ in range(n):
            pass
        return {i: i for i in range(n)}

    def pair(n):
        for _ in range(n):
            pass
        return n, [n]

    def arr(n):
        a = np.zeros(n)
        for i in range(n):
            a[i] = i
        return a

    def early(n):
        acc = set()
        for i in range(n):
            if i > 3:
                return acc
            acc.add(i)
        return None

    def frozen(n):
        out = []
        for i in range(n):
            out.append(i)
        return tuple(out)

    def scalar(n):
        out = []
        for i in range(n):
            out.append(i)
        return len(out)

    def inner_list_not_returned(n):
        def helper():
            return []
        for _ in range(n):
            helper()
        return n
''')


def test_a_function_returning_a_new_mutable_container_is_not_a_candidate(tmp_path):
    p = tmp_path / "returns.py"
    p.write_text(RETURNS_MUTABLE, encoding="utf-8")
    assert _names(p) == {"frozen", "scalar", "inner_list_not_returned"}


def test_a_module_function_named_like_a_method_is_no_mutation_and_aliases_are_followed(tmp_path):
    p = tmp_path / "modfuncs.py"
    p.write_text(textwrap.dedent('''
        import numpy as np

        def summed(a, b, n):
            for _ in range(n):
                a = np.add(a, b)
                np.insert(a, 0, 1)
            return float(np.sort(a)[0])

        def alias_return(n):
            a = []
            for i in range(n):
                a.append(i)
            c = b
            b = a
            return c
    '''), encoding="utf-8")
    assert _names(p) == {"summed"}


def test_open_makes_a_function_impure_and_file_io_is_not_an_indicator(tmp_path):
    p = tmp_path / "io.py"
    p.write_text("def reader(p):\n    for _ in range(3):\n        with open(p) as f:\n            f\n",
                 encoding="utf-8")
    assert _names(p) == set()
    tree = __import__("ast").parse(p.read_text(encoding="utf-8"))
    assert "file_io" not in fcc.is_expensive_computation(tree.body[0])


# --- CLI ---------------------------------------------------------------------------------

def test_cli_reports_a_candidate_and_exits_0(tmp_path, run_script):
    p = tmp_path / "pure.py"
    p.write_text(PURE_BODY, encoding="utf-8")
    r = run_script(SCRIPT, str(p))
    assert r.returncode == 0, r.stderr
    assert b"Found 1 potential candidates" in r.stdout
    assert b"square_sum()" in r.stdout


def test_cli_unparseable_file_exits_2_and_still_prints_the_report(tmp_path, run_script):
    good = tmp_path / "pure.py"
    good.write_text(PURE_BODY, encoding="utf-8")
    bad = tmp_path / "bad.py"
    bad.write_text("def (oops:\n", encoding="utf-8")
    r = run_script(SCRIPT, str(bad), str(good))
    assert r.returncode == 2
    assert b"ERROR" in r.stderr and b"bad.py" in r.stderr
    assert b"Found 1 potential candidates" in r.stdout


def test_cli_directory_argument_exits_2(tmp_path, run_script):
    r = run_script(SCRIPT, str(tmp_path))
    assert r.returncode == 2
    assert b"ERROR" in r.stderr


def test_cli_missing_path_exits_2_and_names_it(tmp_path, run_script):
    missing = tmp_path / "does_not_exist.py"
    r = run_script(SCRIPT, str(missing))
    assert r.returncode == 2
    assert b"not found" in r.stderr and b"does_not_exist.py" in r.stderr


def test_cli_no_arguments_prints_usage_and_exits_2(run_script):
    r = run_script(SCRIPT)
    assert r.returncode == 2
    assert b"usage" in r.stderr.lower()
    assert b"Found" not in r.stdout


def test_cli_help_exits_0_without_scanning(run_script):
    r = run_script(SCRIPT, "--help")
    assert r.returncode == 0
    assert b"usage" in r.stdout.lower()
    assert b"Found" not in r.stdout


def test_cli_non_ansi_path_under_cp1252_stdout_is_written_as_utf8(tmp_path, run_script, clean_env):
    d = tmp_path / "proj_\u7530\u4e2d"
    d.mkdir()
    p = d / "pure.py"
    p.write_text(PURE_BODY, encoding="utf-8")
    r = run_script(SCRIPT, str(p), env=clean_env(PYTHONIOENCODING="cp1252"))
    assert r.returncode == 0, r.stderr
    assert "proj_\u7530\u4e2d" in r.stdout.decode("utf-8")
