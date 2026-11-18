def next_question_index(current_index, question_count, waiting_for_host):
    """Advance only after the current question's result has been published."""
    if not waiting_for_host or current_index >= question_count:
        return None
    return current_index + 1


def next_stage(phase, action):
    """Return the next server-authoritative stage, or None for an invalid action.

    Result publication is driven by the server timer; reveal and advance are
    explicitly controlled by the authenticated Host at the API boundary.
    """
    transitions = {
        ('question', 'time_expired'): 'result',
        ('result', 'reveal_leaderboard'): 'leaderboard',
        ('leaderboard', 'next_question'): 'question',
        ('leaderboard', 'finish_game'): 'completed',
    }
    return transitions.get((phase, action))
