def compute_meta_stats_for_instruction_driven_chat(conversation_history):
    """
    Calculate meta stats for instruction-driven chat.

    Args:
        conversation_history (list): List of dicts, each containing 'prompt' and 'output'.

    Returns:
        dict: Meta statistics JSON with 'prompts_word_count' and 'number_of_turns'.
    """
    number_of_words = sum(
        len(entry["prompt"].split()) for entry in conversation_history
    )
    number_of_turns = len(conversation_history)

    meta_stats = {
        "prompts_word_count": number_of_words,
        "number_of_turns": number_of_turns,
    }

    return meta_stats
