<View>
  <Style>.ant-input { font-size: large; }</Style>
  <View style="font-size: large; display: grid; grid-template: auto/1fr 1fr; column-gap: 1em">
    <Header size="3" value="Source Conversation"/>
    <Header size="3" value="$language Translation"/>
    <Repeater on="$conversation_json" indexFlag="{{idx}}">
      <View style="margin: 0 0 4px;">
        <Text name="speaker_{{idx}}" value="$conversation_json[{{idx}}].id" />
      </View>
      <Repeater on="$conversation_json[{{idx}}].sentences" indexFlag="{{idx2}}">
        <View style="margin: 0 0 24px; background: #d9d9d9; border-radius: 1px; padding: 5px;">
          <Text name="dialogue_{{idx}}_{{idx2}}" value="$conversation_json[{{idx}}].sentences[{{idx2}}]" />
        </View>
      </Repeater>
    </Repeater>
    <Repeater on="$conversation_json" indexFlag="{{idx}}">
      <Text name="output_speaker_{{idx}}" value="$conversation_json[{{idx}}].id" />
      <Repeater on="$conversation_json[{{idx}}].sentences" indexFlag="{{idx2}}">
        <TextArea name="output_{{idx}}_{{idx2}}" toName="dialogue_{{idx}}_{{idx2}}" value="$conversation_json[{{idx}}].sentences[{{idx2}}]" />
      </Repeater>
    </Repeater>
  </View>
</View>