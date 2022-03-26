<View>
  <Image name="file_url" value="$file_url"/>

  <Labels name="annotation_labels" toName="file_url">
    <Label value="Header" background="green"/>
    <Label value="Body" background="blue"/>
    <Label value="Footer" background="orange"/>
  </Labels>

  <Rectangle name="annotation_bboxes" toName="file_url" strokeWidth="3"/>

  <TextArea name="annotation_transcripts" toName="file_url"
            editable="true"
            perRegion="true"
            required="true"
            maxSubmissions="1"
            rows="5"
            placeholder="Recognized Text"
            displayMode="region-list"
            />
</View>
