<View>
  <Header value="Verify the given translation with the machine translation and enter the correct translation"/>
  <Header value="Input Translation"/>
  <Text name="input_text" value="$input_text" />
  <Header value="Input Language" />
  <Text name="input_lang_id" value="$input_lang_id" />
  <Header value="Input Machine Translation" />
  <Text name="input_machine_translation" value="$input_machine_translation" />
  <Header value="Output Translation" />
  <TextArea name="output_text" toName ="input_text" showSubmitButton="true" maxSubmissions="1" editable="true" required="true"/>
</View>