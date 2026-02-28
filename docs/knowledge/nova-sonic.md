Introducing Amazon Nova Sonic: Human-like voice conversations for generative AI applications

July 16, 2025: Amazon Nova Sonic now supports French, Italian, and German, expanding its existing coverage of English and Spanish with six additional expressive voices offering both masculine and feminine-sounding options.

June 12, 2025: Amazon Nova Sonic now also supports Spanish language with two additional (masculine and feminine-sounding) expressive voices.

April 14, 2025: Post updated to clarify the context size.

Voice interfaces are essential to enhance customer experience in different areas such as customer support call automation, gaming, interactive education, and language learning. However, there are challenges when building voice-enabled applications.

Traditional approaches in building voice-enabled applications require complex orchestration of multiple models, such as speech recognition to convert speech to text, language models to understand and generate responses, and text-to-speech to convert text back to audio.

This fragmented approach not only increases development complexity but also fails to preserve crucial linguistic context such as tone, prosody, and speaking style that are essential for natural conversations. This can affect conversational AI applications that need low latency and nuanced understanding of verbal and non-verbal cues for fluid dialog handling and natural turn-taking.

To streamline the implementation of speech-enabled applications, today we are introducing Amazon Nova Sonic, the newest addition to the Amazon Nova family of foundation models (FMs) available in Amazon Bedrock.

Amazon Nova Sonic unifies speech understanding and generation into a single model that developers can use to create natural, human-like conversational AI experiences with low latency and industry-leading price performance. This integrated approach streamlines development and reduces complexity when building conversational applications.

Its unified model architecture delivers expressive speech generation and real-time text transcription without requiring a separate model. The result is an adaptive speech response that dynamically adjusts its delivery based on prosody, such as pace and timbre, of input speech.

When using Amazon Nova Sonic, developers have access to function calling (also known as tool use) and agentic workflows to interact with external services and APIs and perform tasks in the customer’s environment, including knowledge grounding with enterprise data using Retrieval-Augmented Generation (RAG).

At launch, Amazon Nova Sonic provides robust speech understanding for American and British English across various speaking styles and acoustic conditions, with additional languages coming soon.

Amazon Nova Sonic is developed with responsible AI at the forefront of innovation, featuring built-in protections for content moderation and watermarking.

Amazon Nova Sonic in action
The scenario for this demo is a contact center in the telecommunication industry. A customer reaches out to improve their subscription plan, and Amazon Nova Sonic handles the conversation.

With tool use, the model can interact with other systems and use agentic RAG with Amazon Bedrock Knowledge Bases to gather updated, customer-specific information such as account details, subscription plans, and pricing info.

The demo shows streaming transcription of speech input and displays streaming speech responses as text. The sentiment of the conversation is displayed in two ways: a time chart illustrating how it evolves, and a pie chart representing the overall distribution. There’s also an AI insights section providing contextual tips for a call center agent. Other interesting metrics shown in the web interface are the overall talk time distribution between the customer and the agent, and the average response time.

During the conversation with the support agent, you can observe through the metrics and hear in the voices how customer sentiment improves.

The video includes an example of how Amazon Nova Sonic handles interruptions smoothly, stopping to listen and then continuing the conversation in a natural way.

Now, let’s explore how you can integrate voice capabilities in your applications.

Using Amazon Nova Sonic
To get started with Amazon Nova Sonic, you first need to toggle model access in the Amazon Bedrock console, similar to how you would enable other FMs. Navigate to the Model access section of the navigation pane, find Amazon Nova Sonic under the Amazon models, and enable it for your account.

Amazon Bedrock provides a new bidirectional streaming API (InvokeModelWithBidirectionalStream) to help you implement real-time, low-latency conversational experiences on top of the HTTP/2 protocol. With this API, you can stream audio input to the model and receive audio output in real time, so that the conversation flows naturally.

You can use Amazon Nova Sonic with the new API with this model ID: amazon.nova-sonic-v1:0

After the session initialization, where you can configure inference parameters, the model operate through an event-driven architecture on both the input and output streams.

There are three key event types in the input stream:

System prompt – To set the overall system prompt for the conversation

Audio input streaming – To process continuous audio input in real-time

Tool result handling – To send the result of tool use calls back to the model (after tool use is requested in the output events)

Similarly, there are three groups of events in the output streams:

Automatic speech recognition (ASR) streaming – Speech-to-text transcript is generated, containing the result of realtime speech recognition.

Tool use handling – If there are a tool use events, they need to be handled using the information provided here, and the results sent back as input events.

Audio output streaming – To play output audio in real-time, a buffer is needed, because Amazon Nova Sonic model generates audio faster than real-time playback.

You can find examples of using Amazon Nova Sonic in the Amazon Nova model cookbook repository.

Prompt engineering for speech
When crafting prompts for Amazon Nova Sonic, your prompts should optimize content for auditory comprehension rather than visual reading, focusing on conversational flow and clarity when heard rather than seen.

When defining roles for your assistant, focus on conversational attributes (such as warm, patient, concise) rather than text-oriented attributes (detailed, comprehensive, systematic). A good baseline system prompt might be:

You are a friend. The user and you will engage in a spoken dialog exchanging the transcripts of a natural real-time conversation. Keep your responses short, generally two or three sentences for chatty scenarios.

More generally, when creating prompts for speech models, avoid requesting visual formatting (such as bullet points, tables, or code blocks), voice characteristic modifications (accent, age, or singing), or sound effects.

Things to know
Amazon Nova Sonic is available today in the US East (N. Virginia) AWS Region. Visit Amazon Bedrock pricing to see the pricing models.

Amazon Nova Sonic can understand speech in different speaking styles and generates speech in expressive voices, including both masculine-sounding and feminine-sounding voices, in different English accents, including American and British. Support for additional languages will be coming soon.

Amazon Nova Sonic handles user interruptions gracefully without dropping the conversational context and is robust to background noise. The model supports a 300K context window, with a default connection time limit of 8 minutes. However, you can extend your session by establishing a new connection and passing the previous chat history as context.