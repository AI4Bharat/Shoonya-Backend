<View>
  <Style>.ant-input { font-size: large; }</Style>
  <View style="font-size: large; display: grid; grid-template: auto/1fr 1fr; column-gap: 1em">
    <Header size="3" value="Source sentence"/>
    <Header size="3" value="Translated Sentence"/>
    <Text name="input_text" value="$input_text"/>
    <Text name="output_text" value="$output_text"/>
  </View>
  <View>
    <Header size="3" value="Rating"/>
    <Choices name="rating" toName="output_text" choice="single">
    	<Choice value="0, The two sentences are completely dissimilar." />
    	<Choice value="1, The two sentences are not equivalent, but are on the same topic." />
    	<Choice value="2, The two sentences are not equivalent, but share some details" />
    	<Choice value="3, The two sentences are roughly equivalent, but some important information differs/missing." />
    	<Choice value="4, The two sentences are mostly equivalent, but some unimportant details differ." />
    	<Choice value="5, The two sentences are completely equivalent, as they mean the same thing." />
  	</Choices>
  </View>
</View>