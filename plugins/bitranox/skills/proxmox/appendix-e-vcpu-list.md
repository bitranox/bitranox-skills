# QEMU vCPU List

*[Main Index](SKILL.md)*


## E.1 Introduction


This is a list of AMD and Intel x86-64/amd64 CPU types as defined in QEMU, going back to 2007.


## E.2 Intel CPU Types


Intel processors

- Nahelem : 1st generation of the Intel Core processor
- Nahelem-IBRS (v2) : add Spectre v1 protection (+spec-ctrl)
- Westmere : 1st generation of the Intel Core processor (Xeon E7-)
- Westmere-IBRS (v2) : add Spectre v1 protection (+spec-ctrl)
- SandyBridge : 2nd generation of the Intel Core processor
- SandyBridge-IBRS (v2) : add Spectre v1 protection (+spec-ctrl)
- IvyBridge : 3rd generation of the Intel Core processor
- IvyBridge-IBRS (v2): add Spectre v1 protection (+spec-ctrl)
- Haswell : 4th generation of the Intel Core processor
- Haswell-noTSX (v2) : disable TSX (-hle, -rtm)
- Haswell-IBRS (v3) : re-add TSX, add Spectre v1 protection (+hle, +rtm, +spec-ctrl)
- Haswell-noTSX-IBRS (v4) : disable TSX (-hle, -rtm)
- Broadwell: 5th generation of the Intel Core processor
- Skylake: 1st generation Xeon Scalable server processors
- Skylake-IBRS (v2) : add Spectre v1 protection, disable CLFLUSHOPT (+spec-ctrl, -clflushopt)


- Skylake-noTSX-IBRS (v3) : disable TSX (-hle, -rtm)
- Skylake-v4: add EPT switching (+vmx-eptp-switching)
- Cascadelake: 2nd generation Xeon Scalable processor
- Cascadelake-v2 : add arch_capabilities msr (+arch-capabilities, +rdctl-no, +ibrs-all, +skip-l1dfl-vmentry,
+mds-no)

- Cascadelake-v3 : disable TSX (-hle, -rtm)
- Cascadelake-v4 : add EPT switching (+vmx-eptp-switching)
- Cascadelake-v5 : add XSAVES (+xsaves, +vmx-xsaves)
- Cooperlake : 3rd generation Xeon Scalable processors for 4 & 8 sockets servers
- Cooperlake-v2 : add XSAVES (+xsaves, +vmx-xsaves)
- Icelake: 3rd generation Xeon Scalable server processors
- Icelake-v2 : disable TSX (-hle, -rtm)
- Icelake-v3 : add arch_capabilities msr (+arch-capabilities, +rdctl-no, +ibrs-all, +skip-l1dfl-vmentry, +mdsno, +pschange-mc-no, +taa-no)

- Icelake-v4 : add missing flags (+sha-ni, +avx512ifma, +rdpid, +fsrm, +vmx-rdseed-exit, +vmx-pml, +vmxeptp-switching)

- Icelake-v5 : add XSAVES (+xsaves, +vmx-xsaves)
- Icelake-v6 : add "5-level EPT" (+vmx-page-walk-5)
- SapphireRapids : 4th generation Xeon Scalable server processors


## E.3 AMD CPU Types


AMD processors

- Opteron_G3 : K10
- Opteron_G4 : Bulldozer
- Opteron_G5 : Piledriver
- EPYC : 1st generation of Zen processors
- EPYC-IBPB (v2) : add Spectre v1 protection (+ibpb)
- EPYC-v3 : add missing flags (+perfctr-core, +clzero, +xsaveerptr, +xsaves)
- EPYC-Rome : 2nd generation of Zen processors
- EPYC-Rome-v2 : add Spectre v2, v4 protection (+ibrs, +amd-ssbd)
- EPYC-Milan : 3rd generation of Zen processors
- EPYC-Milan-v2 : add missing flags (+vaes, +vpclmulqdq, +stibp-always-on, +amd-psfd, +no-nested-databp, +lfence-always-serializing, +null-sel-clr-base)

## See also

- [VM Hardware Settings (CPU)](ch10-qemu/vm-settings-hardware.md)

