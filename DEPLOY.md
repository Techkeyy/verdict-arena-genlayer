# Deploying Verdict Arena

## Requirements
- Access to https://studio.genlayer.com
- A funded wallet on GenLayer testnet

## Steps
1. Open https://studio.genlayer.com
2. Click "New Contract" and paste the contents of `contracts/verdict_arena.py`
3. Click "Deploy" — no constructor arguments needed
4. Copy your contract address from the Studio UI

## Running a Round
1. Host calls `open_round()` — fetches this week's live debate topic
2. Share the topic with players via Discord
3. Players call `submit_argument("a" or "b", "their argument text")`
4. After 5-10 minutes, host calls `judge_all()`
5. Anyone calls `get_leaderboard()` to see XP results



