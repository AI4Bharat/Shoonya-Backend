def create_memory(result):
    memory = {}
    for i in range(len(result)):
        try:
            key = result[i]["id"]
            dict_type = result[i]["from_name"]
        except KeyError:
            print(
                f"The entry number {i} is not having an id or from_name hence cannot be converted to chitralekha format"
            )
            del result[i]
            continue
        if key not in memory:
            memory[key] = {
                "labels_dict_idx": -1,
                "text_dict_idx": -1,
                "acoustic_text_dict_idx": -1,
            }
        if dict_type == "labels":
            memory[key]["labels_dict_idx"] = i
        elif dict_type == "acoustic_normalised_transcribed_json":
            memory[key]["acoustic_text_dict_idx"] = i
        elif dict_type == "standardised_transcription":
            memory["standardised_transcription"] = i
        else:
            memory[key]["text_dict_idx"] = i
    return memory


def convert_result_to_chitralekha_format(result, ann_id, project_type):
    if (len(result) == 1 and result[0] == {}) or len(result) == 0:
        return []
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
        acoustic_text_dict_idx = memory[result[i]["id"]]["acoustic_text_dict_idx"]
        if labels_dict_idx == -1:
            text_dict = result[text_dict_idx]
            if acoustic_text_dict_idx != -1:
                acoustic_dict = result[acoustic_text_dict_idx]
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
            if acoustic_text_dict_idx != -1:
                acoustic_dict = result[acoustic_text_dict_idx]
                seen.add(acoustic_text_dict_idx)
            seen.add(labels_dict_idx)
            seen.add(text_dict_idx)
            try:
                speaker_id = label_dict["value"]["labels"][0]
            except KeyError:
                speaker_id = "Speaker 0"

        text = text_dict["value"]["text"][0] if text_dict["value"]["text"] else ""
        if acoustic_text_dict_idx != -1:
            acoustic_normalised_text = (
                acoustic_dict["value"]["text"][0]
                if acoustic_dict["value"]["text"]
                else ""
            )
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
            if acoustic_text_dict_idx != -1:
                chitra_dict["acoustic_normalised_text"] = acoustic_normalised_text
        except Exception:
            continue
        count += 1

        modified_result.append(chitra_dict)
    modified_result = (
        sort_result_by_start_time(modified_result) if len(modified_result) > 0 else []
    )
    if (
        project_type == "AcousticNormalisedTranscriptionEditing"
        and "standardised_transcription" in memory.keys()
        and result[memory["standardised_transcription"]]["value"]["text"]
    ):
        modified_result.append(
            {
                "standardised_transcription": result[
                    memory["standardised_transcription"]
                ]["value"]["text"][0]
            }
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
        return "00:00:00.000"
    if decimal_time < 0:
        return "00:00:00.000"
    if isinstance(decimal_time, str):
        try:
            decimal_time = float(decimal_time)
        except ValueError:
            print(
                f"The data is corrupt for annotation id-{ann_id}, data id- {data_id}. "
                f"Failed to convert '{decimal_time}' to a valid numeric format."
            )
            return "00:00:00.000"

    hours = int(decimal_time // 3600)
    remaining_minutes = int((decimal_time % 3600) // 60)
    seconds = int(decimal_time % 60)
    milliseconds = int((decimal_time - int(decimal_time)) * 1000)

    return f"{hours:02d}:{remaining_minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def sort_result_by_start_time(result):
    sorted_result = sorted(result, key=lambda x: x["start_time"])
    return sorted_result
