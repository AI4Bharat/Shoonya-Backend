<View>
  <Header value="Translate the given sentence into the specified language"/>

  <Header value="Input Sentence"/>
  <Text name="input_text" value="$input_text" />

  <Header value="Translation Language (Output Language)" />
  <Text name="output_lang_id" value="$output_lang_id" />

  <Header value="Translation" />
  <TextArea name="output_text" toName="input_text" showSubmitButton="true" maxSubmissions="1" editable="true" required="true"/>

</View>
