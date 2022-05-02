<View>
  <View style="font-size: large; display: grid; grid-template: auto/1fr 1fr 1fr 1fr; column-gap: 1em">
    <Header size="3" value="Source sentence"/>
    <Header size="3" value="Context"/>
    <Header size="3" value="$output_language translation"/>
    <Header size="3" value="Machine translation"/>
    <Text name="input_text" value="$input_text"/>
    <Text name="context" value="$context"/>
    <TextArea name="output_text" toName="input_text" value="$machine_translation" rows="5" transcription="true" showSubmitButton="true" maxSubmissions="1" editable="true" required="true"/>
    <Text name="machine_translation" value="$machine_translation"/>
  </View>
</View>
