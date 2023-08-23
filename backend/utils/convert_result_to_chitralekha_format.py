def create_memory(result):
    memory = {}
    for i in range(len(result)):
        try:
            key = result[i]["id"]
        except KeyError:
            print(
                f"The entry number {i} is not having an id hence cannot be converted to CL_format"
            )
            del result[i]
            continue
        if key not in memory:
            memory[key] = {"labels_dict_idx": -1, "text_dict_idx": -1}
        if result[i]["type"] == "labels":
            memory[key]["labels_dict_idx"] = i
        else:
            memory[key]["text_dict_idx"] = i
    return memory


def convert_result_to_chitralekha_format(result, ann_id):
    if len(result) == 1 and result[0] == {}:
        return [{}]
    memory = create_memory(result)
    modified_result = []
    count = 1
    seen = set()
    for i in range(len(result)):
        if i in seen:
            continue
        labels_dict_idx, text_dict_idx = (
            memory[result[i]["id"]]["labels_dict_idx"],
            memory[result[i]["id"]]["text_dict_idx"],
        )
        if labels_dict_idx == -1:
            text_dict = result[text_dict_idx]
            speaker_id = "Speaker 0"
            seen.add(text_dict_idx)
        elif text_dict_idx == -1:
            print(
                f"The data is corrupt for annotation id-{ann_id}, data id- {result[i]['id']}. "
                f"It does not contain a corresponding text dictionary."
            )
            continue
        else:
            label_dict = result[labels_dict_idx]
            text_dict = result[text_dict_idx]
            seen.add(labels_dict_idx)
            seen.add(text_dict_idx)
            speaker_id = label_dict["value"]["labels"][0]
        text = text_dict["value"]["text"][0] if text_dict["value"]["text"] else ""
        try:
            chitra_dict = {
                "text": text,
                "end_time": convert_fractional_time_to_formatted(
                    text_dict["value"]["end"], ann_id, text_dict["id"]
                ),
                "speaker_id": speaker_id,
                "start_time": convert_fractional_time_to_formatted(
                    text_dict["value"]["start"], ann_id, text_dict["id"]
                ),
                "id": count,
            }
        except Exception:
            continue
        count += 1

        modified_result.append(chitra_dict)
    modified_result = (
        sort_result_by_start_time(modified_result) if len(modified_result) > 0 else []
    )
    return modified_result


def convert_fractional_time_to_formatted(decimal_time, ann_id, data_id):
    if not (
        isinstance(decimal_time, str)
        or isinstance(decimal_time, int)
        or isinstance(decimal_time, float)
    ):
        print(
            f"The data is corrupt for annotation id-{ann_id}, data id- {data_id}. "
            f"Its start/end time are not stored as proper data type (int or float or string)."
        )
    decimal_time = float(decimal_time)
    hours = int(decimal_time // 60)
    remaining_minutes = int(decimal_time % 60)
    seconds_fraction = decimal_time - ((hours * 60) + remaining_minutes)
    seconds = int(seconds_fraction * 60)
    milliseconds = int((seconds_fraction * 60 - seconds) * 1000)

    return f"{hours:02d}:{remaining_minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def sort_result_by_start_time(result):
    sorted_result = sorted(result, key=lambda x: x["start_time"])
    return sorted_result
