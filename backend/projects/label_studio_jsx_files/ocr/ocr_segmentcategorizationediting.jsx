<View>
  <Image name="image_url" value="$image_url"/>
  
  <Labels name="annotation_labels" toName="image_url" className="ignore_assertion">
    
    <Label value="title" background="green" name="title"/>
    <Label value="text" background="blue" name="text"/>
    <Label value="image" background="red" name="image"/>
    <Label value="unord-list" background="yellow" name="unord-list"/>
    <Label value="ord-list" background="black" name="ord-list"/>
    <Label value="placeholder" background="orange" name="placeholder"/>
    <Label value="table" background="violet" name="table"/>
    <Label value="dateline" background="cyan" name="dateline"/>
    <Label value="byline" background="brown" name="byline"/>
    <Label value="page-number" background="purple" name="page-number"/>
    <Label value="footer" background="indigo" name="footer"/>
    <Label value="footnote" background="pink" name="footnote"/>
    <Label value="header" background="olive" name="header"/>
    <Label value="social-media-handle" background="aqua" name="social-media-handle"/>
    <Label value="website-link" background="teal" name="website-link"/>
    <Label value="caption" background="maroon" name="caption"/>
    <Label value="table-header" background="aquamarine" name="table-header"/>
    
  </Labels>

  <Rectangle name="annotation_bboxes" toName="image_url" strokeWidth="3" className="ignore_assertion"/>
  
  <Choices visibleWhen="region-selected" whenTagName="annotation_labels" whenLabelValue="title" name="title_opts" toName="image_url">
  	<Choice value="h1" />
    <Choice value="h2" />
    <Choice value="h3" />
  </Choices>
  
  <Choices visibleWhen="region-selected" whenTagName="annotation_labels" whenLabelValue="text" name="text_opts" toName="image_url">
  	<Choice value="paragraph" />
    <Choice value="foreign-language-text" />
  </Choices>
  
  <Choices visibleWhen="region-selected" whenTagName="annotation_labels" whenLabelValue="image" name="image_opts" toName="image_url">
  	<Choice value="img" />
    <Choice value="logo" />
    <Choice value="formula" />
    <Choice value="equation" />
    <Choice value="bg-img" />
  </Choices>
  
  <Choices visibleWhen="region-selected" whenTagName="annotation_labels" whenLabelValue="placeholder" name="placeholder_opts" toName="image_url">
  	<Choice value="placeholder-txt" />
    <Choice value="placeholder-img" />
  </Choices>
  
  <Choices visibleWhen="region-selected" whenTagName="annotation_labels" whenLabelValue="caption" name="caption_opts" toName="image_url">
  	<Choice value="fig-caption" />
    <Choice value="table-caption" />
  </Choices>
    
</View>


