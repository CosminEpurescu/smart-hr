package com.ing.parser.scraper;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.ing.parser.model.Job;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.util.List;

/**
 * Main orchestrator for ING Careers scraping.
 * Coordinates job listing scraping, detail extraction, and output.
 */
@Service
public class IngCareersScraper {

    private static final Logger log = LoggerFactory.getLogger(IngCareersScraper.class);

    private final JobListingScraper listingScraper;
    private final JobDetailScraper detailScraper;
    private final ObjectMapper objectMapper;

    public IngCareersScraper(JobListingScraper listingScraper, JobDetailScraper detailScraper) {
        this.listingScraper = listingScraper;
        this.detailScraper = detailScraper;
        this.objectMapper = createObjectMapper();
    }

    private ObjectMapper createObjectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());
        mapper.enable(SerializationFeature.INDENT_OUTPUT);
        mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        return mapper;
    }

    /**
     * Runs the complete scraping process.
     * 
     * @param outputPath Path to save the JSON output
     * @param limit      Maximum number of jobs to scrape (0 = unlimited)
     * @return List of scraped jobs
     */
    public List<Job> scrape(String outputPath, int limit) {
        log.info("Starting ING Careers scraping (limit: {})", limit == 0 ? "unlimited" : limit);

        // Step 1: Get all job URLs
        log.info("Step 1: Scraping job listing URLs...");
        List<String> jobUrls = listingScraper.scrapeJobUrls(limit);
        log.info("Found {} job URLs to process", jobUrls.size());

        if (jobUrls.isEmpty()) {
            log.warn("No job URLs found, exiting");
            return List.of();
        }

        // Step 2: Scrape each job detail page
        log.info("Step 2: Scraping job details...");
        List<Job> jobs = detailScraper.scrapeJobs(jobUrls);
        log.info("Successfully scraped {} jobs", jobs.size());

        // Step 3: Save to JSON
        if (outputPath != null && !outputPath.isEmpty()) {
            saveToJson(jobs, outputPath);
        }

        return jobs;
    }

    /**
     * Saves jobs to a JSON file.
     */
    public void saveToJson(List<Job> jobs, String outputPath) {
        try {
            File file = new File(outputPath);
            File parentDir = file.getParentFile();
            if (parentDir != null && !parentDir.exists()) {
                parentDir.mkdirs();
            }

            objectMapper.writeValue(file, jobs);
            log.info("Saved {} jobs to {}", jobs.size(), outputPath);
        } catch (IOException e) {
            log.error("Failed to save jobs to {}: {}", outputPath, e.getMessage());
        }
    }

    /**
     * Convenience method to get summary statistics.
     */
    public String getStatistics(List<Job> jobs) {
        if (jobs.isEmpty())
            return "No jobs scraped";

        long withDescription = jobs.stream().filter(j -> j.getDescription() != null).count();
        long withRequirements = jobs.stream().filter(j -> j.getRequirements() != null && !j.getRequirements().isEmpty())
                .count();

        return String.format("""
                Scraping Statistics:
                - Total jobs: %d
                - With description: %d (%.1f%%)
                - With requirements: %d (%.1f%%)
                """,
                jobs.size(),
                withDescription, (100.0 * withDescription / jobs.size()),
                withRequirements, (100.0 * withRequirements / jobs.size()));
    }
}
