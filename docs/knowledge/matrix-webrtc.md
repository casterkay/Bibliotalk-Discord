# WebRTC Communication

The matrix-js-sdk provides comprehensive WebRTC capabilities for real-time audio and video communication in Matrix rooms. The system consists of core classes that handle call signaling, media management, and peer-to-peer connections.

For information about the encryption systems used for secure communications, see [End-to-End Encryption](/matrix-org/matrix-js-sdk/5-end-to-end-encryption).

## Overview

The matrix-js-sdk provides two main WebRTC communication systems:

1.  **One-to-One Calls**: Direct calls between two users, implemented through the `MatrixCall` class
2.  **Group Calls**: Multi-party calls with mesh topology, implemented through the `GroupCall` class

The SDK manages all aspects of WebRTC communication:

-   Matrix event-based signaling (`m.call.*` events)
-   Media stream acquisition via `MediaHandler`
-   WebRTC peer connection management
-   Call state transitions and error handling
-   Media feed management through `CallFeed` objects
-   Features like screensharing, muting, and active speaker detection

## Architecture

### Core WebRTC Components

Event Processing

WebRTC Primitives

Media Handling

Call Management Classes

MatrixClient Integration

creates on m.call.invite

creates from room state

manages multiple

getUserMediaStream()

getScreensharingStream()

provides local feeds

manages

aggregates

peerConn

stream

addTrack()

handles

handles

MatrixClient

CallEventHandler

GroupCallEventHandler

MediaHandler

MatrixCall

GroupCall

CallFeed\[\]

RTCPeerConnection

MediaStream

m.call.invite/answer/candidates

m.call state events

Sources:

-   [src/webrtc/call.ts356-471](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/call.ts#L356-L471)
-   [src/webrtc/groupCall.ts226-296](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L226-L296)
-   [src/webrtc/callEventHandler.ts48-84](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callEventHandler.ts#L48-L84)
-   [src/webrtc/groupCallEventHandler.ts46-114](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCallEventHandler.ts#L46-L114)
-   [src/webrtc/callFeed.ts70-119](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callFeed.ts#L70-L119)
-   [src/webrtc/mediaHandler.ts52-68](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/mediaHandler.ts#L52-L68)

## One-to-One Calls

One-to-one calls are managed by the `MatrixCall` class, which handles the entire lifecycle of a WebRTC call between two users.

### MatrixCall State Machine

"new MatrixCall()"

"placeVoiceCall()/placeVideoCall()"

"initWithInvite()"

"getUserMediaStream() complete"

"answer() called"

"createOffer() and sendInvite()"

"createAnswer() and sendAnswer()"

"ICE connected"

"remote ringing"

"onAnswerReceived()"

"hangup()/onHangupReceived()"

"terminate() on error"

"hangup()/timeout"

"CallErrorCode.\*"

Fledgling

InviteSent

WaitLocalMedia

CreateOffer

CreateAnswer

Connecting

Connected

Ringing

Ended

Any State

Sources:

-   [src/webrtc/call.ts105-115](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/call.ts#L105-L115)
-   [src/webrtc/call.ts477-487](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/call.ts#L477-L487)
-   [src/webrtc/call.ts944-1010](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/call.ts#L944-L1010)

### Call Signaling Protocol

Matrix calls use Matrix events for WebRTC signaling, processed by `CallEventHandler`:

"MatrixCall (Callee)""CallEventHandler""Matrix Server""CallEventHandler""MatrixCall (Caller)""MatrixCall (Callee)""CallEventHandler""Matrix Server""CallEventHandler""MatrixCall (Caller)"par\[ICE Candidate Exchange\]"RTCPeerConnection established""placeVoiceCall()""m.call.invite + SDP offer""m.call.invite event""handleCallEvent()""createNewMatrixCall()""initWithInvite()""answer()""m.call.answer + SDP answer""m.call.answer event""onAnswerReceived()""m.call.candidates""onRemoteIceCandidatesReceived()""m.call.candidates""onRemoteIceCandidatesReceived()""m.call.hangup""onHangupReceived()"

Sources:

-   [src/webrtc/callEventHandler.ts192-424](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callEventHandler.ts#L192-L424)
-   [src/webrtc/call.ts944-1010](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/call.ts#L944-L1010)
-   [src/webrtc/call.ts1686-1746](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/call.ts#L1686-L1746)

### CallFeed Media Stream Management

The `CallFeed` class wraps `MediaStream` objects with metadata and audio analysis:

"manages"

"categorizes by"

"emits"

CallFeed

+stream: MediaStream

+sdpMetadataStreamId: string

+userId: string

+deviceId: string

+purpose: SDPStreamMetadataPurpose

+speakingVolumeSamples: number\[\]

+isLocal() : : boolean

+isAudioMuted() : : boolean

+isVideoMuted() : : boolean

+setAudioVideoMuted(audioMuted, videoMuted) : : void

+measureVolumeActivity(enabled) : : void

+isSpeaking() : : boolean

+clone() : : CallFeed

+dispose() : : void

«enumeration»

CallFeedEvent

NewStream

MuteStateChanged

VolumeChanged

Speaking

Disposed

«enumeration»

SDPStreamMetadataPurpose

Usermedia

Screenshare

MediaStream

Sources:

-   [src/webrtc/callFeed.ts70-119](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callFeed.ts#L70-L119)
-   [src/webrtc/callFeed.ts50-58](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callFeed.ts#L50-L58)
-   [src/webrtc/callEventTypes.ts9-12](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callEventTypes.ts#L9-L12)

## Group Calls

Group calls coordinate multiple `MatrixCall` peer connections through the `GroupCall` class to create mesh topology communication.

### GroupCall Architecture and Components

Active Speaker Detection

Participant Management

GroupCall Class Structure

clone() for each

clone() for each

remote feeds

remote feeds

Media Distribution

GroupCall

calls: Map>

localCallFeed: CallFeed

localScreenshareFeed: CallFeed

participants: Map>

userMediaFeeds: CallFeed\[\]

screenshareFeeds: CallFeed\[\]

participantTimeout cleanup

updateParticipants()

onActiveSpeakerLoop()

activeSpeaker: CallFeed

Sources:

-   [src/webrtc/groupCall.ts226-295](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L226-L295)
-   [src/webrtc/groupCall.ts381-403](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L381-L403)
-   [src/webrtc/groupCall.ts574-578](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L574-L578)

### GroupCall State Machine

"new GroupCall()"

"initLocalCallFeed()"

"getUserMediaStream() complete"

"enter() without local feed"

"enter()"

"leave()"

"terminate()"

"terminate()"

"terminate()"

"terminate()"

LocalCallFeedUninitialized

InitializingLocalCallFeed

LocalCallFeedInitialized

Entered

Ended

Sources:

-   [src/webrtc/groupCall.ts200-206](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L200-L206)
-   [src/webrtc/groupCall.ts471-565](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L471-L565)
-   [src/webrtc/groupCall.ts627-656](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L627-L656)

### Group Call Signaling and State Events

Group calls use Matrix state events processed by `GroupCallEventHandler`:

User2GroupCall"GroupCallEventHandler""Matrix Server"User1User2GroupCall"GroupCallEventHandler""Matrix Server"User1"EventType.GroupCallPrefix""EventType.GroupCallMemberPrefix""Multiple MatrixCall peer connections established""m.call state event""room state change""createGroupCallFromRoomStateEvent()""GroupCallEventHandlerEvent.Incoming""create() and enter()""m.call.member state event""m.call.member state event""updateParticipants()""onRetryCallLoop()""createNewMatrixCall() for peer"

Sources:

-   [src/webrtc/groupCallEventHandler.ts139-200](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCallEventHandler.ts#L139-L200)
-   [src/webrtc/groupCall.ts329-362](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L329-L362)
-   [src/webrtc/groupCall.ts556-578](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L556-L578)

## Event Processing

The WebRTC system relies on two event handlers to process Matrix events and manage call lifecycles.

### CallEventHandler Processing

The `CallEventHandler` processes individual call events and manages `MatrixCall` instances:

Event Type

Handler Method

Purpose

`m.call.invite`

`handleCallEvent()`

Creates new `MatrixCall`, calls `initWithInvite()`

`m.call.answer`

`handleCallEvent()`

Calls `onAnswerReceived()` on existing call

`m.call.candidates`

`handleCallEvent()`

Calls `onRemoteIceCandidatesReceived()`

`m.call.hangup`

`handleCallEvent()`

Calls `onHangupReceived()`

`m.call.reject`

`handleCallEvent()`

Calls `onRejectReceived()`

The handler includes sequence number enforcement for to-device events and buffering for out-of-order delivery.

Sources:

-   [src/webrtc/callEventHandler.ts192-424](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callEventHandler.ts#L192-L424)
-   [src/webrtc/callEventHandler.ts143-189](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callEventHandler.ts#L143-L189)

### GroupCallEventHandler Processing

The `GroupCallEventHandler` monitors room state events and manages `GroupCall` instances:

EventType.GroupCallPrefix

Other

Valid

Invalid

Room State Change

Event Type?

createGroupCallFromRoomStateEvent()

Ignore

Validate m.type, m.intent

new GroupCall()

Log warning, ignore

groupCalls.set(roomId, groupCall)

emit(GroupCallEventHandlerEvent.Incoming)

Sources:

-   [src/webrtc/groupCallEventHandler.ts139-200](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCallEventHandler.ts#L139-L200)
-   [src/webrtc/groupCallEventHandler.ts206-233](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCallEventHandler.ts#L206-L233)

## Media Handling

The `MediaHandler` class manages media device access, stream reuse, and provides unified media stream management across all calls.

### MediaHandler Class Structure

"uses"

"emits"

MediaHandler

+userMediaStreams: MediaStream\[\]

+screensharingStreams: MediaStream\[\]

\-audioInput: string

\-videoInput: string

\-audioSettings: AudioSettings

\-localUserMediaStream: MediaStream

+getUserMediaStream(audio, video, reusable) : : Promise

+getScreensharingStream(opts, reusable) : : Promise

+setAudioInput(deviceId) : : Promise

+setVideoInput(deviceId) : : Promise

+setAudioSettings(opts) : : Promise

+hasAudioDevice() : : Promise

+hasVideoDevice() : : Promise

+updateLocalUsermediaStreams() : : Promise

+stopUserMediaStream(stream) : : void

+stopScreensharingStream(stream) : : void

+stopAllStreams() : : void

AudioSettings

+autoGainControl: boolean

+echoCancellation: boolean

+noiseSuppression: boolean

«enumeration»

MediaHandlerEvent

LocalStreamsChanged

### Stream Management and Reuse

The `MediaHandler` implements sophisticated stream reuse logic:

1.  **Stream Caching**: `localUserMediaStream` is reused when constraints match
2.  **Device Synchronization**: Updates all active calls when media devices change
3.  **Constraint Matching**: Compares audio/video requirements and device IDs before creating new streams
4.  **Cleanup Management**: Automatically stops unused streams and removes them from arrays

Sources:

-   [src/webrtc/mediaHandler.ts52-68](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/mediaHandler.ts#L52-L68)
-   [src/webrtc/mediaHandler.ts216-316](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/mediaHandler.ts#L216-L316)
-   [src/webrtc/mediaHandler.ts130-188](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/mediaHandler.ts#L130-L188)

## Integration and Usage

### Client Initialization

WebRTC functionality is integrated into `MatrixClient` through dedicated handler instances:

```
// CallEventHandler manages individual callsclient.callEventHandler = new CallEventHandler(client);client.callEventHandler.start(); // GroupCallEventHandler manages group calls  client.groupCallEventHandler = new GroupCallEventHandler(client);client.groupCallEventHandler.start();
```

### Creating and Managing Calls

**One-to-One Call Creation:**

```
import { createNewMatrixCall } from 'matrix-js-sdk'; const call = createNewMatrixCall(client, roomId, options);await call.placeVoiceCall(); // or placeVideoCall()
```

**Group Call Creation:**

```
const groupCall = new GroupCall(    client,     room,     GroupCallType.Video,     false, // isPtt     GroupCallIntent.Prompt);await groupCall.create();await groupCall.enter();
```

**Event Listening:**

```
// Listen for incoming callsclient.on(CallEventHandlerEvent.Incoming, (call: MatrixCall) => {    // Handle incoming MatrixCall    call.answer();}); // Listen for group callsclient.on(GroupCallEventHandlerEvent.Incoming, (groupCall: GroupCall) => {    // Handle incoming GroupCall    await groupCall.enter();});
```

Sources:

-   [src/webrtc/callEventHandler.ts74-84](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callEventHandler.ts#L74-L84)
-   [src/webrtc/groupCallEventHandler.ts57-84](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCallEventHandler.ts#L57-L84)
-   [src/webrtc/call.ts477-487](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/call.ts#L477-L487)
-   [src/webrtc/groupCall.ts329-336](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L329-L336)

## Advanced Features

### Data Channels

Both `MatrixCall` and `GroupCall` support WebRTC data channels for real-time data exchange:

```
// Create data channel on MatrixCallconst dataChannel = call.createDataChannel("myChannel", {    ordered: true,    maxRetransmits: 5}); // Listen for data channel eventscall.on(CallEvent.DataChannel, (channel, call) => {    // Handle new data channel});
```

Group calls can configure data channels through constructor parameters:

```
const groupCall = new GroupCall(    client, room, GroupCallType.Video,     false, // isPtt    GroupCallIntent.Prompt,    groupCallId,    true, // dataChannelsEnabled    dataChannelOptions // IGroupCallDataChannelOptions);
```

Sources:

-   [src/webrtc/call.ts494-498](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/call.ts#L494-L498)
-   [src/webrtc/groupCall.ts160-178](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L160-L178)

### Call Statistics and Monitoring

The SDK provides comprehensive call statistics through dedicated reporting systems:

```
// Individual call statisticsconst callStats = await call.getCurrentCallStats(); // Group call statistics eventsgroupCall.on(GroupCallStatsReportEvent.ConnectionStats, ({ report }) => {    // Handle connection statistics}); groupCall.on(GroupCallStatsReportEvent.SummaryStats, ({ report }) => {    // Handle summary statistics});
```

Statistics include connection quality metrics, bandwidth usage, packet loss, and media quality data.

Sources:

-   [src/webrtc/call.ts918-938](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/call.ts#L918-L938)
-   [src/webrtc/groupCall.ts297-327](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/groupCall.ts#L297-L327)

## Error Handling and Call Management

### Call Error Codes

The `CallErrorCode` enum defines specific error conditions that can occur during calls:

Error Code

Description

Typical Cause

`UserHangup`

User intentionally ended call

User clicked hangup

`NoUserMedia`

Cannot access media devices

Permission denied or no hardware

`UnknownDevices`

Unknown devices in encrypted room

E2EE device verification needed

`IceFailed`

WebRTC connection failed

Network/firewall issues

`InviteTimeout`

Remote party didn't answer

Call rang too long

`CreateOffer`/`CreateAnswer`

SDP negotiation failed

WebRTC setup error

### Feed Management

`CallFeed` objects emit events for media state changes:

```
feed.on(CallFeedEvent.MuteStateChanged, (audioMuted, videoMuted) => {    // Handle mute state changes}); feed.on(CallFeedEvent.Speaking, (speaking) => {    // Handle speaking detection}); feed.on(CallFeedEvent.VolumeChanged, (volume) => {    // Handle volume level changes  });
```

The `CallFeed.measureVolumeActivity()` method enables real-time audio level monitoring and speaking detection using WebAudio APIs.

Sources:

-   [src/webrtc/call.ts160-249](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/call.ts#L160-L249)
-   [src/webrtc/callFeed.ts50-68](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callFeed.ts#L50-L68)
-   [src/webrtc/callFeed.ts258-310](https://github.com/matrix-org/matrix-js-sdk/blob/41d70d0b/src/webrtc/callFeed.ts#L258-L310)

## Summary

The matrix-js-sdk provides a comprehensive WebRTC implementation with three main systems:

1.  **MatrixCall**: For one-to-one calls with full support for voice, video, and screensharing
2.  **GroupCall**: For multi-party calls with a mesh topology
3.  **MatrixRTC**: A newer system with room sessions and media encryption

These systems handle all aspects of WebRTC communication, from signaling and media management to encryption and statistics, making it straightforward to implement real-time communication in Matrix client applications.
