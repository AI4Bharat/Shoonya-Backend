<View>
  <Style>.ant-input { font-size: large; }</Style>
  <View style="font-size: large; display: grid; grid-template: auto/1fr 1fr 1fr; column-gap: 1em">
    <Header size="3" value="Source sentence"/>
    <Header size="3" value="$output_language translation"/>
    <Header size="3" value="Machine translation"/>
    <Text name="input_text" value="$input_text"/>
    <TextArea name="output_text" toName="input_text" value="$machine_translation" rows="5" transcription="true" showSubmitButton="true" maxSubmissions="1" editable="false" required="true"/>
    <Text name="machine_translation" value="$machine_translation"/>
  </View>
  <View style="font-size: large; display: grid; grid-template: auto; column-gap: 1em">
    <Header size="3" value="Context"/>
    <Text name="context" value="$context"/>
  </View>
</View>
