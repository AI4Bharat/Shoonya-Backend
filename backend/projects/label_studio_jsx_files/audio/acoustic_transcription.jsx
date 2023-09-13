<View>

  <Header value="Speaker Details" />
  {speaker_0_details ?
    <Text name="speaker_0_details" className="ignore_assertion"
      value="$speaker_0_details" /> : null}
  {speaker_1_details ?
    <Text name="speaker_1_details" className="ignore_assertion"
      value="$speaker_1_details" /> : null}

  <Labels name="labels" toName="audio_url" className="ignore_assertion">
    {speaker_0_details ? <Label value="Speaker 0" /> : null}
    {speaker_1_details ? <Label value="Speaker 1" /> : null}
  </Labels>
  <AudioPlus name="audio_url" value="$audio_url" />

  <View visibleWhen="region-selected">
    <Header value="Provide Transcription" />
  </View>
  <View style="overflow: auto; width: 50%;">
    <TextArea name="verbatim_transcribed_json" transcription="true" toName="audio_url" 
      rows="2" editable="false" maxSubmissions="1"
      perRegion="true" required="true" className="ignore_assertion"/>
  </View>
  <View style="display: none;">
    <TextArea name="acoustic_normalised_transcribed_json" toName="audio_url" perRegion="true" className="ignore_assertion" />
    <TextArea name="standardised_transcription" toName="audio_url" className="ignore_assertion"/>
  </View>
  {reference_raw_transcript ? <Header value="Reference Transcript" /> 
   <Text name="reference_raw_transcript" 
    value="$reference_raw_transcript"/> : null}

</View >

