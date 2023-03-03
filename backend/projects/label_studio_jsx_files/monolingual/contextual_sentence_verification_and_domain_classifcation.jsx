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
<View visibleWhen="choice-selected" whenTagName="quality_status" whenChoiceValue="Clean"
style="font-size: large; display: grid; grid-template: auto; column-gap: 1em">
  <Header size="3" value="Domain"/> 
 <Taxonomy name="domain" toName="text" maxUsages="1" required="true">
      <Choice value="None" selected="true"/>
      <Choice value="General" />
      <Choice value="News" />
      <Choice value="Education" />
      <Choice value="Legal" />
      <Choice value="Government-Press-Release" />
      <Choice value="Healthcare" />
      <Choice value="Agriculture" />
      <Choice value="Automobile" />
      <Choice value="Tourism" />
      <Choice value="Financial" />
      <Choice value="Movies" />
      <Choice value="Subtitles" />
      <Choice value="Sports" />
      <Choice value="Technology" />
      <Choice value="Lifestyle" />
      <Choice value="Entertainment" />
      <Choice value="Parliamentary" />
      <Choice value="Art-and-Culture" />
      <Choice value="Economy" />
      <Choice value="History" />
      <Choice value="Philosophy" />
      <Choice value="Religion"/>
      <Choice value="National-Security-and-Defence"/>
      <Choice value="Literature"/>
      <Choice value="Geography"/>
  	</Taxonomy>
</View>
  <View style="font-size: large; display: grid; grid-template: auto; column-gap: 1em">
    <Header size="3" value="Context"/>
    <Text name="context" value="$context"/>
  </View>
</View>
