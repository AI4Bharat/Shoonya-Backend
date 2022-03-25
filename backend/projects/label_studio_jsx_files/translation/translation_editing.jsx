<View>
  <Header value="Verify the given translation with the machine translation and enter the correct translation"/>
  <Header value="Input Translation"/>
  <Text name="input_text" value="$input_text" />
  <Header value="Output Language" />
  <Text name="output_lang_id" value="$output_lang_id" />
  <Header value="Machine Translation" />
  <Text name="machine_translation" value="$machine_translation" />
  <Header value="Output Translation" />
  <TextArea name="output_text" toName ="input_text" showSubmitButton="true" maxSubmissions="1" editable="true" required="true"/>
</View>
