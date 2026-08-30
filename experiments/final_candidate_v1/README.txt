FinCluster FINAL-CANDIDATE v1
=============================

PURPOSE
-------
Create and collect a controlled 1,000-transaction PaySim benchmark AFTER the
v0.6 reproducibility validation passed for Low60 / Medium75 / High100.

IMPORTANT
---------
This package calls the outputs FINAL-CANDIDATE, not FINAL TRAINING DATA.
The dataset is promoted only after collection completeness and quality audit.

FROZEN WORKING PROTOCOL
-----------------------
- PaySim sample: 1,000 transactions total, 200 per transaction type
- Sampling: deterministic per-type reservoir sampling over the full source
- Seed: 20260829
- 10 randomized/balanced blocks of 100 transactions (20/type/block)
- Processor: existing reference_processor.py v0.3 (unchanged)
- Docker image: fincluster-pilot:0.3
- CPU period: 10000 us
- cpuset: CPU 0 only
- thread env limits: OMP/OpenBLAS/MKL/NumExpr = 1
- Low: 60% CPU / 1 GB
- Medium: 75% CPU / 2 GB
- High: 100% CPU / 4 GB
- 2 warmups + 5 measured runs per transaction-node pair
- primary target: median service_time_ms
- node order rotates by block: LMH, MHL, HLM, repeat
- recommended host sessions: blocks 1-5, clean restart, blocks 6-10

FILES TO PLACE
--------------
Research\experiments\final_candidate_v1\
  final.ps1
  final_tool.py
  README.txt

SHORT COMMANDS (run from Research root)
---------------------------------------
1) Prepare fixed sample and block files:
   .\experiments\final_candidate_v1\final.ps1 prepare

2) After verifying prepare output, clean-restart and run blocks one at a time:
   .\experiments\final_candidate_v1\final.ps1 block 1
   .\experiments\final_candidate_v1\final.ps1 block 2
   ...
   .\experiments\final_candidate_v1\final.ps1 block 10

3) After all 10 blocks:
   .\experiments\final_candidate_v1\final.ps1 audit

DO NOT
------
- do not rerun a completed block/node: the tool refuses to overwrite evidence
- do not alter the sample, processor, Docker image, quota, cpuset, thread limits,
  warmups, or measured-run count mid-collection
- do not mix v0.5/v0.6 diagnostic data into this final-candidate dataset
