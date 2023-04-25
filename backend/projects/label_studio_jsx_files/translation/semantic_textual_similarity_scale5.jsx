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
            <Choice alias="1" value="1, Two sentences are not equivalent, share very little details, and may be about different topics." />
            <Choice alias="2" value="2, Two sentences share some details, but are not equivalent." />
            <Choice alias="3" value="3, Two sentences are mostly equivalent, but some unimportant details can differ." />
            <Choice alias="4" value="4, Two sentences are paraphrases of each other. Their meanings are near-equivalent, with no major differences or information missing." />
            <Choice alias="5" value="5, Two sentences are exactly and completely equivalent in meaning and usage expression." />
        </Choices>
    </View>
</View>
