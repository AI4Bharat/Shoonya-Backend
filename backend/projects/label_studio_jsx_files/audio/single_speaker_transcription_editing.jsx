<View> 
  <Labels name="labels" toName="audio_url" className="ignore_assertion"> 
    <Label value="Speaker" /> 
    <Label value="Noise" /> 
  </Labels> 
  <AudioPlus name="audio_url" value="$audio_url"/> 
  
  <View visibleWhen="region-selected"> 
    <Header value="Provide Transcription" /> 
  </View> 
  
  <TextArea name="transcribed_json" toName="audio_url" 
            rows="2" editable="true" 
            perRegion="true" required="true" /> 
   
  {reference_raw_transcript ? <Text name="reference_raw_transcript" 
value="$reference_raw_transcript"/> : null} 
   
</View> 
 