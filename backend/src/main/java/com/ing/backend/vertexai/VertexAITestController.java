package com.ing.backend.vertexai;


import com.google.cloud.aiplatform.v1.EndpointServiceClient;
import com.google.cloud.aiplatform.v1.EndpointServiceSettings;
import com.google.cloud.aiplatform.v1.LocationName;
import com.google.cloud.aiplatform.v1.Endpoint;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.ResponseEntity;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

@RestController
public class VertexAITestController {

    private final String projectId = "ai-deniers-486907";
    private final String location = "us-central1";

    @GetMapping("/test-vertex-ai-connection")
    public ResponseEntity<String> testVertexAIConnection() {
        try {
            EndpointServiceSettings endpointServiceSettings = EndpointServiceSettings.newBuilder()
                    .setEndpoint(location + "-aiplatform.googleapis.com:443")
                    .build();

            try (EndpointServiceClient client = EndpointServiceClient.create(endpointServiceSettings)) {
                LocationName parent = LocationName.of(projectId, location);

                List<String> endpointNames = new ArrayList<>();
                // Try to list endpoints. This will test authentication and API access.
                // Even if you have no endpoints, the call should succeed without an authentication error.
                for (Endpoint endpoint : client.listEndpoints(parent).iterateAll()) {
                    endpointNames.add(endpoint.getDisplayName());
                }

                if (endpointNames.isEmpty()) {
                    return ResponseEntity.ok("Successfully connected to Vertex AI and found no deployed endpoints in region " + location + " for project " + projectId + ". This indicates basic API access is working.");
                } else {
                    return ResponseEntity.ok("Successfully connected to Vertex AI and found deployed endpoints: " + String.join(", ", endpointNames) + " in region " + location + " for project " + projectId + ". This indicates basic API access is working.");
                }

            }
        } catch (IOException e) {
            // This could be due to network issues or credential problems.
            e.printStackTrace();
            return ResponseEntity.status(500).body("Error communicating with Vertex AI. Check network and GOOGLE_APPLICATION_CREDENTIALS: " + e.getMessage());
        } catch (Exception e) {
            // Catch any other unexpected errors, potentially related to permissions.
            e.printStackTrace();
            return ResponseEntity.status(500).body("An unexpected error occurred while testing Vertex AI connection: " + e.getMessage());
        }
    }
}

