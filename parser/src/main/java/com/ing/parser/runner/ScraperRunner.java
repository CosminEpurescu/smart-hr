package com.ing.parser.runner;

import com.ing.parser.model.Job;
import com.ing.parser.scraper.IngCareersScraper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Command-line runner for the ING Careers scraper.
 * 
 * Usage:
 * mvn spring-boot:run -Dspring-boot.run.arguments="--output=./jobs.json
 * --limit=10"
 * 
 * Arguments:
 * --output=<path> : Output JSON file path (default: ./ing_jobs.json)
 * --limit=<number> : Maximum jobs to scrape, 0 for all (default: 0)
 * --skip : Skip scraping (for testing)
 */
@Component
public class ScraperRunner implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(ScraperRunner.class);

    private final IngCareersScraper scraper;

    public ScraperRunner(IngCareersScraper scraper) {
        this.scraper = scraper;
    }

    @Override
    public void run(String... args) throws Exception {
        String outputPath = "./ing_jobs.json";
        int limit = 0;
        boolean skip = false;

        // Parse command-line arguments
        for (String arg : args) {
            if (arg.startsWith("--output=")) {
                outputPath = arg.substring("--output=".length());
            } else if (arg.startsWith("--limit=")) {
                try {
                    limit = Integer.parseInt(arg.substring("--limit=".length()));
                } catch (NumberFormatException e) {
                    log.warn("Invalid limit value, using default (0 = unlimited)");
                }
            } else if (arg.equals("--skip")) {
                skip = true;
            }
        }

        if (skip) {
            log.info("Scraping skipped due to --skip flag");
            return;
        }

        log.info("=== ING Careers Scraper ===");
        log.info("Output: {}", outputPath);
        log.info("Limit: {}", limit == 0 ? "unlimited" : limit);
        log.info("===========================");

        long startTime = System.currentTimeMillis();

        List<Job> jobs = scraper.scrape(outputPath, limit);

        long duration = (System.currentTimeMillis() - startTime) / 1000;

        log.info("\n{}", scraper.getStatistics(jobs));
        log.info("Scraping completed in {} seconds", duration);
        log.info("Output saved to: {}", outputPath);
    }
}
