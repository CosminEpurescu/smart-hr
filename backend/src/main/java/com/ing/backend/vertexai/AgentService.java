package com.ing.backend.vertexai;

import com.google.cloud.dialogflow.cx.v3.*;
import org.springframework.stereotype.Service;

import java.io.IOException;

@Service
public class AgentService {

    private final String projectId = "ai-deniers-486907";
    private final String location = "europe-west3";  // Change to your agent's location
    private final String agentId = "Subagent_google_search_agent";  // Replace with your agent ID from Vertex AI

    public String chat(String userMessage, String sessionId) throws IOException {
        String endpoint = location + "-dialogflow.googleapis.com:443";
        
        SessionsSettings sessionsSettings = SessionsSettings.newBuilder()
                .setEndpoint(endpoint)
                .build();

        try (SessionsClient sessionsClient = SessionsClient.create(sessionsSettings)) {
            SessionName session = SessionName.of(projectId, location, agentId, sessionId);

            TextInput textInput = TextInput.newBuilder()
                    .setText(userMessage)
                    .build();

            QueryInput queryInput = QueryInput.newBuilder()
                    .setText(textInput)
                    .setLanguageCode("en")
                    .build();

            DetectIntentRequest request = DetectIntentRequest.newBuilder()
                    .setSession(session.toString())
                    .setQueryInput(queryInput)
                    .build();

            DetectIntentResponse response = sessionsClient.detectIntent(request);
            
            StringBuilder result = new StringBuilder();
            for (ResponseMessage message : response.getQueryResult().getResponseMessagesList()) {
                if (message.hasText()) {
                    for (String text : message.getText().getTextList()) {
                        result.append(text);
                    }
                }
            }
            
            return result.length() > 0 ? result.toString() : "No response from agent";
        }
    }
}
