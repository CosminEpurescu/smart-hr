package com.ing.backend.vertexai;

import com.google.cloud.vertexai.VertexAI;
import com.google.cloud.vertexai.generativeai.GenerativeModel;
import com.google.cloud.vertexai.api.GenerateContentResponse;
import com.google.cloud.vertexai.generativeai.ResponseHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.http.ResponseEntity;
import java.util.HashMap;
import java.util.Map;

@RestController
public class VertexAITestController {

    private final String projectId = "ai-deniers-486907";
    private final String location = "europe-west4";

    @PostMapping("/scoring-agent")
    public ResponseEntity<Map<String, Object>> scoringAgent(@RequestBody ScoringRequest request) {
        final String agentName = "Scoring_model";
        final String modelName = "gemini-2.5-flash";
        final String agentDescription = "Agent to help give a score given a parsed CV as an input and a list of jobs with full descriptions.";
        final String instruction = """
            You are a CV scoring agent. Your task is to analyze a parsed CV and compare it against job descriptions.
            For each job, provide a compatibility score from 0-100 and explain your reasoning.
            
            Consider the following factors:
            - Skills match
            - Experience relevance
            - Education requirements
            - Keywords alignment
            
            Provide your response in JSON format with scores and explanations for each job.
            """;

        try (VertexAI vertexAI = new VertexAI(projectId, location)) {
            GenerativeModel model = new GenerativeModel.Builder()
                    .setModelName(modelName)
                    .setVertexAi(vertexAI)
                    .build();

            // Build the prompt combining instruction, CV, and jobs
            String prompt = String.format("""
                %s
                
                ## Parsed CV:
                %s
                
                ## Job Descriptions:
                %s
                
                Please score the CV against each job and provide detailed feedback.
                """, instruction, request.getCv(), request.getJobs());

            GenerateContentResponse response = model.generateContent(prompt);
            String responseText = ResponseHandler.getText(response);

            Map<String, Object> result = new HashMap<>();
            result.put("agentName", agentName);
            result.put("model", modelName);
            result.put("description", agentDescription);
            result.put("response", responseText);

            return ResponseEntity.ok(result);

        } catch (Exception e) {
            e.printStackTrace();
            Map<String, Object> error = new HashMap<>();
            error.put("error", "Error running scoring agent: " + e.getMessage());
            return ResponseEntity.status(500).body(error);
        }
    }

    /**
     * Request DTO for the scoring agent
     */
    public static class ScoringRequest {
        private String cv;
        private String jobs;

        public String getCv() { return cv; }
        public void setCv(String cv) { this.cv = cv; }
        public String getJobs() { return jobs; }
        public void setJobs(String jobs) { this.jobs = jobs; }
    }
}

