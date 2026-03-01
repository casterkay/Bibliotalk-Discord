export function mixAgentStreams(streams, activeSpeakerId) {
  // For strict turn-taking, only the active speaker is returned.
  return streams.filter((stream) => stream.agentId === activeSpeakerId);
}
