def convert_result_to_chitralekha_format(result):
    result = sort_array_by_start(result)
    modified_result = []
    count = 1
    for i in range(1, len(result), 2):
        label_dict = result[i - 1]
        text_dict = result[i]
        text = text_dict["value"]["text"][0] if text_dict["value"]["text"] else ""
        chitra_dict = {
            "text": text,
            "end_time": convert_fractional_time_to_formatted(text_dict["value"]["end"]),
            "speaker_id": label_dict["value"]["labels"][0],
            "start_time": convert_fractional_time_to_formatted(
                text_dict["value"]["start"]
            ),
            "id": count,
        }
        count += 1

        modified_result.append(chitra_dict)

    return modified_result


def convert_fractional_time_to_formatted(minutes):
    total_seconds = minutes * 60

    hours = int(total_seconds // 3600)
    total_seconds %= 3600

    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60

    formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
    return formatted_time


def sort_array_by_start(array):
    def sort_key(entry):
        return entry["value"]["start"]

    sorted_array = sorted(array, key=sort_key)
    return sorted_array
