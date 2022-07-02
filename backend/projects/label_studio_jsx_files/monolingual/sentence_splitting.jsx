<View>
  <Style>.ant-input { font-size: large; }</Style>
  <Header size="3" value="Block Text"/>
  <View style="font-size: large">
    <Text name="text" value="$text" />
  </View>
  <Header size="3" value="Split into Sentences" />
  <View style="font-size: large">
    <TextArea name="splitted_text" toName ="text" rows="20" showSubmitButton="true" maxSubmissions="1" editable="true" required="true"/>
  </View>
</View>
