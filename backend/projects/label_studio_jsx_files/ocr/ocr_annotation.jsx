<View>
  <Image name="image_url" value="$image_url"/>

  <Labels name="annotation_labels" toName="image_url">
    <Label value="Header" background="green"/>
    <Label value="Body" background="blue"/>
    <Label value="Footer" background="orange"/>
  </Labels>

  <Rectangle name="annotation_bboxes" toName="image_url" strokeWidth="3"/>

  <TextArea name="annotation_transcripts" toName="image_url"
            editable="true"
            perRegion="true"
            required="true"
            maxSubmissions="1"
            rows="5"
            placeholder="Recognized Text"
            displayMode="region-list"
            />
</View>
