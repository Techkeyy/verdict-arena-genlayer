# Verdict Arena 🏟️ — A GenLayer Community Mini-Game

A weekly AI debate game built on GenLayer Intelligent Contracts.

## How It Works
Every week, the contract fetches a live trending topic from Hacker News.
Players submit arguments defending one side. The LLM — via Optimistic Democracy
consensus — scores each argument on Logic, Creativity, and Persuasiveness.
XP is distributed on-chain through a live leaderboard.

## GenLayer Mechanics Used
- `gl.get_webpage()` — live topic fetch each week
- `gl.exec_prompt()` — LLM scoring of player arguments  
- `eq_principle_strict_eq` — consensus on topic selection
- `eq_principle_prompt_non_comparative` — consensus on subjective scoring
- `TreeMap[Address, u256]` — on-chain leaderboard & XP tracking

## Game Flow (5-12 minutes)
1. Host calls `open_round()` → live topic auto-fetched
2. Players call `submit_argument("a" or "b", "your argument")`
3. Host calls `judge_all()` → AI scores all submissions
4. Anyone calls `get_leaderboard()` → XP results displayed

## Deployed Contract
Network: GenLayer Testnet
Address: [0xb034718b09A88A7eA237677C6343fd2Abb39Ca7D]

## Setup
Deploy `contracts/verdict_arena.py` in https://studio.genlayer.com
No constructor arguments needed.
