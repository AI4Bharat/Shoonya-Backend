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
        <Choices name="rating" toName="output_text" choice="single-radio" required="true" requiredMessage="Please select a rating for the translation">
            <Choice alias="0" value="0, Two sentences are completely dissimilar." />
            <Choice alias="1" value="1, Two sentences are not equivalent, and only minor details match, the majority part of the sentences does not match. At least sentences should be of related topics." />
            <Choice alias="2" value="2, Two sentences are roughly equivalent, but some important information differs/is missing." />
            <Choice alias="3" value="3, Two sentences are mostly equivalent, but some unimportant details can differ." />
            <Choice alias="4" value="4, Two sentences are completely equivalent, as they mean the same thing." />
        </Choices>
    </View>
</View>
