<View>
  <Style>.ant-input { font-size: large; }</Style>
  <View style="font-size: large; display: grid; grid-template: auto/1fr 1fr 1fr; column-gap: 1em">
    <Header size="3" value="$language Sentence"/>
    <Header size="3" value="Corrected Sentence"/>
    <Header size="3" value="Quality Status"/>
    <Text name="text" value="$text"/>
    <TextArea name="corrected_text" toName="text" value="$text" rows="5" transcription="true" showSubmitButton="true" maxSubmissions="1" editable="false" required="true"/>
  	<Choices name="quality_status" toName="text" choice="single-radio" required="true">
    	<Choice value="Clean" selected="true"/>
    	<Choice value="Profane" />
      <Choice value="Difficult vocabulary" />
      <Choice value="Ambiguous sentence" />
      <Choice value="Context incomplete" />
    	<Choice value="Corrupt" />
  	</Choices>
  </View>
  <View style="font-size: large; display: grid; grid-template: auto; column-gap: 1em">
    <Header size="3" value="Context"/>
    <Text name="context" value="$context"/>
  </View>
</View>
