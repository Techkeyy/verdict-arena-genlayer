# { "Depends": "py-genlayer:test" }

from genlayer import *

import json
import typing


# ─────────────────────────────────────────────────────────────────────────────
# VERDICT ARENA — A GenLayer Community Mini-Game
#
# Concept:
#   Every week, the contract fetches a REAL controversial or debatable topic
#   from the web (trending tech debates, crypto takes, AI opinions, etc.).
#   Players submit their ARGUMENT defending one side.
#   The LLM — via Optimistic Democracy consensus — judges each argument on
#   logic, creativity, and persuasiveness, awarding XP points.
#   A live leaderboard tracks the top debaters across all rounds.
#
# GenLayer mechanics used:
#   • gl.get_webpage()            — fetches the week's real debate topic live
#   • gl.exec_prompt()            — LLM scores each player's argument
#   • eq_principle_strict_eq      — consensus on deterministic topic fetch
#   • eq_principle_prompt_non_comparative — consensus on subjective scoring
#   • TreeMap[Address, ...]       — on-chain player registry & scores
#   • gl.message.sender_address   — identity-based submission tracking
#   • gl.message.datetime         — weekly round gating
# ─────────────────────────────────────────────────────────────────────────────


class VerdictArena(gl.Contract):
    # ── Persistent on-chain state ──────────────────────────────────────────
    current_week: str                          # ISO week string e.g. "2025-W10"
    current_topic: str                         # Fetched debate topic for this week
    current_side_a: str                        # e.g. "AI will replace developers"
    current_side_b: str                        # e.g. "AI will augment developers"

    submissions: TreeMap[Address, str]         # player → their argument text
    scores: TreeMap[Address, u256]             # player → XP earned this week
    all_time_xp: TreeMap[Address, u256]        # player → lifetime XP
    player_list: DynArray[Address]             # ordered list of participants

    round_open: bool                           # whether submissions are accepted
    judging_done: bool                         # whether judging has completed
    host: Address                              # deployer / host address

    def __init__(self):
        self.current_week = ""
        self.current_topic = ""
        self.current_side_a = ""
        self.current_side_b = ""
        self.round_open = False
        self.judging_done = False
        self.host = gl.message.sender_address

    # ── HOST: Open a new weekly round ─────────────────────────────────────
    @gl.public.write
    def open_round(self) -> str:
        """
        Host opens a new weekly round.
        Fetches a live trending debate topic from Hacker News or similar source.
        Uses eq_principle_strict_eq so ALL validators agree on the same topic.
        Can only be called once per week (enforced by ISO week string).
        """
        assert gl.message.sender_address == self.host, "Only host can open rounds"
        assert not self.round_open, "A round is already open"

        # Derive ISO week from transaction datetime (format: "YYYY-MM-DDTHH:MM:SSZ")
        dt = gl.message.datetime          # e.g. "2025-03-15T12:00:00Z"
        date_part = dt[:10]               # "2025-03-15"
        year = int(date_part[:4])
        month = int(date_part[5:7])
        day = int(date_part[8:10])

        # Simple ISO week number calculation
        import datetime
        d = datetime.date(year, month, day)
        iso = d.isocalendar()
        week_str = f"{iso[0]}-W{iso[1]:02d}"

        assert week_str != self.current_week, "Round for this week already played"
        self.current_week = week_str

        # ── Non-deterministic: fetch live topic from Hacker News front page ──
        def fetch_topic() -> str:
            hn_page = gl.get_webpage("https://news.ycombinator.com", mode="text")

            prompt = f"""You are a game host for a debate mini-game called Verdict Arena.

From the following Hacker News front page content, identify ONE interesting, 
debate-worthy story or topic that has TWO reasonable opposing sides.

Front page content:
{hn_page[:3000]}

Respond ONLY with this JSON format — nothing else:
{{
    "topic": str,      // The debate topic in 1-2 sentences
    "side_a": str,     // One position (max 10 words)
    "side_b": str      // The opposing position (max 10 words)
}}
No markdown, no extra text. Pure JSON only."""

            result = gl.exec_prompt(prompt).replace("```json", "").replace("```", "").strip()
            parsed = json.loads(result)
            # Sort keys for deterministic string output across validators
            return json.dumps(parsed, sort_keys=True)

        # strict_eq: all validators must agree on EXACTLY the same topic JSON
        topic_json_str = gl.eq_principle_strict_eq(fetch_topic)
        topic_data = json.loads(topic_json_str)

        self.current_topic = topic_data["topic"]
        self.current_side_a = topic_data["side_a"]
        self.current_side_b = topic_data["side_b"]

        # Clear last week's submissions and scores
        for addr in self.player_list:
            del self.submissions[addr]
            del self.scores[addr]
        # Reset player list
        while len(self.player_list) > 0:
            self.player_list.pop()

        self.round_open = True
        self.judging_done = False

        return f"Round {week_str} opened! Topic: {self.current_topic}"

    # ── PLAYER: Submit an argument ─────────────────────────────────────────
    @gl.public.write
    def submit_argument(self, side: str, argument: str) -> str:
        """
        Player submits their argument for side_a or side_b.
        side: must be "a" or "b"
        argument: the player's written argument (max ~500 chars enforced by LLM scoring)
        """
        assert self.round_open, "No round is currently open"
        assert not self.judging_done, "Judging is already complete for this round"
        assert side in ["a", "b"], "side must be 'a' or 'b'"
        assert len(argument) >= 20, "Argument too short — make your case!"
        assert len(argument) <= 600, "Argument too long — keep it under 600 characters"

        player = gl.message.sender_address

        # Track new players
        if self.submissions.get(player, None) is None:
            self.player_list.append(player)

        # Store side prefix with argument so judging knows which side they argued
        self.submissions[player] = f"SIDE_{side.upper()}::{argument}"

        return "Argument submitted! Wait for the host to call judge_all()."

    # ── HOST: Judge all submissions ────────────────────────────────────────
    @gl.public.write
    def judge_all(self) -> str:
        """
        Host triggers judging. The LLM scores EVERY submission using the
        Non-Comparative Equivalence Principle — the most important GenLayer
        mechanic for subjective evaluation.

        Each player's argument is scored 0-100 XP based on:
          - Logic (40pts): Is the reasoning sound?
          - Creativity (30pts): Is the argument original/interesting?
          - Persuasiveness (30pts): Would it change minds?

        Validators don't need to produce identical scores — they just need
        to agree that the leader's score is REASONABLE (non-comparative).
        """
        assert gl.message.sender_address == self.host, "Only host can trigger judging"
        assert self.round_open, "No open round to judge"
        assert not self.judging_done, "Already judged"
        assert len(self.player_list) > 0, "No submissions to judge"

        topic = self.current_topic
        side_a = self.current_side_a
        side_b = self.current_side_b

        # Score each player individually
        for player in self.player_list:
            raw = self.submissions.get(player, "")
            if not raw:
                continue

            # Parse side and argument
            parts = raw.split("::", 1)
            side_tag = parts[0]   # "SIDE_A" or "SIDE_B"
            argument = parts[1] if len(parts) > 1 else ""
            position = side_a if side_tag == "SIDE_A" else side_b

            # Capture for closure
            player_argument = argument
            player_position = position

            def score_argument() -> str:
                prompt = f"""You are an impartial debate judge for the game Verdict Arena.

DEBATE TOPIC: {topic}
PLAYER IS ARGUING FOR: "{player_position}"

PLAYER'S ARGUMENT:
"{player_argument}"

Score this argument on a scale of 0 to 100 total points across three dimensions:
- Logic (0-40): Is the reasoning coherent, well-structured, and factually grounded?
- Creativity (0-30): Is the argument original, interesting, or uses unexpected angles?
- Persuasiveness (0-30): Would this argument genuinely persuade a neutral reader?

Respond ONLY with this JSON:
{{
    "logic": int,
    "creativity": int,
    "persuasiveness": int,
    "total": int,
    "one_line_feedback": str
}}
No markdown. Pure JSON only. total must equal logic + creativity + persuasiveness."""

                result = gl.exec_prompt(prompt).replace("```json", "").replace("```", "").strip()
                return result

            # ── eq_principle_prompt_non_comparative ────────────────────────
            # Validators don't re-score from scratch. They just VERIFY that
            # the leader's score is a reasonable evaluation of the argument.
            # This is the right principle for subjective, qualitative outputs.
            scored_str = gl.eq_principle_prompt_non_comparative(
                score_argument,
                task=f"Score a debate argument about '{topic}' on logic, creativity, and persuasiveness (0-100 total)",
                criteria="""The score JSON is valid if:
1. All fields (logic, creativity, persuasiveness, total, one_line_feedback) are present
2. logic is between 0-40, creativity 0-30, persuasiveness 0-30
3. total equals logic + creativity + persuasiveness
4. The scores are reasonable for the quality of the argument — not all 0s or all max unless justified
5. one_line_feedback is a brief, constructive sentence"""
            )

            scored = json.loads(scored_str)
            xp = u256(min(max(int(scored.get("total", 0)), 0), 100))

            self.scores[player] = xp

            # Add to lifetime XP
            current_all_time = self.all_time_xp.get(player, u256(0))
            self.all_time_xp[player] = current_all_time + xp

        self.round_open = False
        self.judging_done = True

        return "Judging complete! Call get_leaderboard() to see results."

    # ── READ: Weekly leaderboard ───────────────────────────────────────────
    @gl.public.view
    def get_leaderboard(self) -> str:
        """Returns this week's ranked leaderboard as JSON."""
        entries = []
        for player in self.player_list:
            xp = int(self.scores.get(player, u256(0)))
            entries.append({"address": player.as_hex, "xp": xp})

        # Sort descending by XP
        entries.sort(key=lambda e: e["xp"], reverse=True)

        # Add rank
        for i, entry in enumerate(entries):
            entry["rank"] = i + 1

        return json.dumps({
            "week": self.current_week,
            "topic": self.current_topic,
            "leaderboard": entries
        }, indent=2)

    # ── READ: All-time leaderboard ─────────────────────────────────────────
    @gl.public.view
    def get_all_time_leaderboard(self) -> str:
        """Returns the all-time XP leaderboard across all rounds."""
        entries = []
        for player in self.player_list:
            xp = int(self.all_time_xp.get(player, u256(0)))
            entries.append({"address": player.as_hex, "lifetime_xp": xp})

        entries.sort(key=lambda e: e["lifetime_xp"], reverse=True)
        for i, entry in enumerate(entries):
            entry["rank"] = i + 1

        return json.dumps({"all_time_leaderboard": entries}, indent=2)

    # ── READ: Current round info ───────────────────────────────────────────
    @gl.public.view
    def get_round_info(self) -> str:
        """Returns current round state — use this to display the debate topic to players."""
        return json.dumps({
            "week": self.current_week,
            "topic": self.current_topic,
            "side_a": self.current_side_a,
            "side_b": self.current_side_b,
            "round_open": self.round_open,
            "judging_done": self.judging_done,
            "player_count": len(self.player_list)
        }, indent=2)

    # ── READ: Player's own submission ──────────────────────────────────────
    @gl.public.view
    def get_my_score(self, player_address: str) -> str:
        """Returns a specific player's XP for the current round."""
        addr = Address(player_address)
        xp = int(self.scores.get(addr, u256(0)))
        lifetime = int(self.all_time_xp.get(addr, u256(0)))
        return json.dumps({
            "address": player_address,
            "this_week_xp": xp,
            "lifetime_xp": lifetime
        })
