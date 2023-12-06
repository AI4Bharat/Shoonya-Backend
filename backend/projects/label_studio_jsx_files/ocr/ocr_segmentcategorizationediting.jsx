<View>
  <Image name="image_url" value="$image_url"/>
  
  <Labels name="annotation_labels" toName="image_url" className="ignore_assertion">
    
    <Label value="title" background="green" name="title" className="ignore_assertion"/>
    <Label value="text" background="blue" name="text" className="ignore_assertion"/>
    <Label value="image" background="red" name="image" className="ignore_assertion"/>
    <Label value="unord-list" background="yellow" name="unord-list" className="ignore_assertion"/>
    <Label value="ord-list" background="black" name="ord-list" className="ignore_assertion"/>
    <Label value="placeholder" background="orange" name="placeholder" className="ignore_assertion"/>
    <Label value="table" background="violet" name="table" className="ignore_assertion"/>
    <Label value="dateline" background="cyan" name="dateline" className="ignore_assertion"/>
    <Label value="byline" background="brown" name="byline" className="ignore_assertion"/>
    <Label value="page-number" background="purple" name="page-number" className="ignore_assertion"/>
    <Label value="footer" background="indigo" name="footer" className="ignore_assertion"/>
    <Label value="footnote" background="pink" name="footnote" className="ignore_assertion"/>
    <Label value="header" background="olive" name="header" className="ignore_assertion"/>
    <Label value="social-media-handle" background="aqua" name="social-media-handle" className="ignore_assertion"/>
    <Label value="website-link" background="teal" name="website-link" className="ignore_assertion"/>
    <Label value="caption" background="maroon" name="caption" className="ignore_assertion"/>
    <Label value="table-header" background="aquamarine" name="table-header" className="ignore_assertion"/>
    
  </Labels>

  <Rectangle name="annotation_bboxes" toName="image_url" strokeWidth="3" className="ignore_assertion"/>
  
  <Choices visibleWhen="region-selected" whenTagName="annotation_labels" whenLabelValue="title" name="title_opts" toName="image_url" className="ignore_assertion">
  	<Choice value="h1" />
    <Choice value="h2" />
    <Choice value="h3" />
  </Choices>
  
  <Choices visibleWhen="region-selected" whenTagName="annotation_labels" whenLabelValue="text" name="text_opts" toName="image_url" className="ignore_assertion">
  	<Choice value="paragraph" />
    <Choice value="foreign-language-text" />
  </Choices>
  
  <Choices visibleWhen="region-selected" whenTagName="annotation_labels" whenLabelValue="image" name="image_opts" toName="image_url" className="ignore_assertion">
  	<Choice value="img" />
    <Choice value="logo" />
    <Choice value="formula" />
    <Choice value="equation" />
    <Choice value="bg-img" />
  </Choices>
  
  <Choices visibleWhen="region-selected" whenTagName="annotation_labels" whenLabelValue="placeholder" name="placeholder_opts" toName="image_url" className="ignore_assertion">
  	<Choice value="placeholder-txt" />
    <Choice value="placeholder-img" />
  </Choices>
  
  <Choices visibleWhen="region-selected" whenTagName="annotation_labels" whenLabelValue="caption" name="caption_opts" toName="image_url" className="ignore_assertion">
  	<Choice value="fig-caption" />
    <Choice value="table-caption" />
  </Choices>
    
</View>


