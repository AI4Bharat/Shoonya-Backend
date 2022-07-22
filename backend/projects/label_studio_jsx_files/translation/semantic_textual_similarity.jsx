<View>
  <Style>.ant-input { font-size: large; }</Style>
  <View style="font-size: large; display: grid; grid-template: auto/1fr 1fr; column-gap: 1em">
    <Header size="3" value="Source sentence"/>
    <Header size="3" value="Translated Sentence"/>
    <Text name="input_text" value="$input_text"/>
    <Text name="output_text" value="$output_text"/>
  </View>
  <View>
    <Rating name="rating" toName="output_text" defaultValue="0" maxRating="5" size="large" required="true" />
  </View>
</View>
