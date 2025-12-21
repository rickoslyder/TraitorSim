"""Prompt templates for Game Master narrative generation."""

from typing import Dict


class GMPrompts:
    """Prompt templates for Game Master using Gemini."""

    @staticmethod
    def game_start(state, config) -> str:
        """Generate game start announcement prompt."""
        return f"""You are the Game Master for "The Traitors" simulation.

{config.total_players} contestants have arrived at the castle.
{config.num_traitors} of them are Traitors, the rest are Faithful.

Generate a dramatic opening announcement in the style of the TV show's narrator.
Welcome the players and explain the rules:
- Faithfuls must find and banish all Traitors
- Traitors must remain hidden and eliminate Faithfuls
- Every night, Traitors murder a Faithful
- Every day, all players vote to banish someone
- The prize pot is currently ${state.prize_pot:,.0f}

Keep it under 100 words. Make it atmospheric and tense."""

    @staticmethod
    def first_breakfast(state) -> str:
        """Generate first breakfast announcement (no murder yet)."""
        return f"""The players gather for breakfast on Day {state.day}.

This is the first morning. No one has been murdered... yet.

Generate a short, atmospheric announcement welcoming them to breakfast.
Build tension about what's to come.
Current prize pot: ${state.prize_pot:,.0f}

Keep it under 50 words."""

    @staticmethod
    def murder_reveal(victim_name: str, state) -> str:
        """Generate murder reveal announcement."""
        return f"""The players gather for breakfast on Day {state.day}.

One chair is empty. {victim_name} has been murdered during the night.

Generate a dramatic announcement revealing {victim_name}'s death.
Make it suspenseful and foreboding. The castle claims its victims.
Current prize pot: ${state.prize_pot:,.0f}

Keep it under 80 words."""

    @staticmethod
    def mission_intro(mission_description: str) -> str:
        """Generate mission introduction."""
        return f"""It's time for today's mission.

Mission objective: {mission_description}

Generate a dramatic introduction to this mission in the style of a TV narrator.
Build excitement about the challenge ahead.

Keep it under 60 words."""

    @staticmethod
    def mission_result(result, state) -> str:
        """Generate mission result announcement."""
        return f"""The mission has concluded.

{result.narrative}

The prize pot is now ${state.prize_pot:,.0f}.

Generate a short, dramatic announcement about the mission outcome.
Emphasize either the team's success or their failures.

Keep it under 50 words."""

    @staticmethod
    def roundtable_open(state) -> str:
        """Generate Round Table opening."""
        alive_count = len(state.alive_players)
        return f"""The Round Table is about to begin on Day {state.day}.

Current situation:
- Alive: {alive_count} players
- Prize Pot: ${state.prize_pot:,.0f}

Generate a tense opening for the Round Table where players will vote to banish someone.
Remind them that someone here is a Traitor.
Build the dramatic tension.

Keep it under 60 words."""

    @staticmethod
    def banishment(player, votes: Dict, state) -> str:
        """Generate banishment announcement."""
        vote_count = sum(1 for v in votes.values() if v == player.id)
        total_votes = len(votes)

        return f"""The votes have been tallied.

{player.name} received {vote_count} out of {total_votes} votes.

They have been banished from the castle.

{player.name} was a {player.role.value.upper()}.

Generate a dramatic banishment announcement revealing their role.
Make it theatrical and intense.

Keep it under 70 words."""

    @staticmethod
    def finale(winner_role, state) -> str:
        """Generate game finale announcement."""
        if winner_role.value == "faithful":
            winners = [p.name for p in state.players if p.role.value == "faithful" and p.alive]
            winner_text = f"The Faithful have won! {', '.join(winners)} will share the ${state.prize_pot:,.0f} prize pot."
        else:
            winners = [p.name for p in state.players if p.role.value == "traitor" and p.alive]
            winner_text = f"The Traitors have won! {', '.join(winners)} will take the ${state.prize_pot:,.0f} prize pot."

        return f"""The game has ended on Day {state.day}.

{winner_text}

Generate a dramatic finale announcement in the style of the TV show.
Celebrate the winners and reflect on the journey.

Keep it under 100 words."""
