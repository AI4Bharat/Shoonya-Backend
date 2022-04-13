<View>
  <View style="font-size: large; display: grid; grid-template: auto/1fr 1fr 1fr; column-gap: 1em">
    <Header size="3" value="Source sentence"/>
    <Header size="3" value="Machine translation"/>
    <Header size="3" value="$output_lang_id translation"/>
    <Text name="input_text" value="$input_text"/>
    <Text name="machine_translation" value="$machine_translation"/>
    <TextArea name="output_text" toName="input_text" rows="5" transcription="true" showSubmitButton="true" maxSubmissions="1" editable="true" required="true"/>
  </View>
</View>