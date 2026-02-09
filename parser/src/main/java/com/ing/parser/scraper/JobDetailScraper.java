package com.ing.parser.scraper;

import com.ing.parser.config.ScraperConfig;
import com.ing.parser.model.Job;
import org.openqa.selenium.*;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Scrapes individual job detail pages from ING Careers.
 */
@Service
public class JobDetailScraper {

    private static final Logger log = LoggerFactory.getLogger(JobDetailScraper.class);

    private final ScraperConfig config;

    // Date formatters for various date formats
    private static final DateTimeFormatter[] DATE_FORMATTERS = {
            DateTimeFormatter.ofPattern("dd/MM/yyyy"),
            DateTimeFormatter.ofPattern("MM/dd/yyyy"),
            DateTimeFormatter.ofPattern("yyyy-MM-dd"),
            DateTimeFormatter.ofPattern("d MMMM yyyy", Locale.ENGLISH),
            DateTimeFormatter.ofPattern("MMMM d, yyyy", Locale.ENGLISH)
    };

    public JobDetailScraper(ScraperConfig config) {
        this.config = config;
    }

    /**
     * Scrapes job details from a single job URL.
     */
    public Job scrapeJob(String url, WebDriver driver) {
        Job job = new Job();
        job.setSourceUrl(url);

        try {
            // Extract job ID from URL
            Pattern idPattern = Pattern.compile("/job/[^/]+/[^/]+/(\\d+)/(\\d+)");
            Matcher matcher = idPattern.matcher(url);
            if (matcher.find()) {
                job.setId(matcher.group(1) + "-" + matcher.group(2));
            }

            log.info("Navigating to URL: {}", url);
            driver.get(url);
            log.info("Page loaded, waiting for h1...");

            WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(config.getPageLoadTimeout()));
            wait.until(ExpectedConditions.presenceOfElementLocated(By.tagName("h1")));
            log.info("h1 found, extracting data...");

            // Extract title
            job.setTitle(extractText(driver, "h1"));
            log.info("Title extracted: {}", job.getTitle());

            // Extract metadata (location, department, etc.)
            extractMetadata(driver, job);
            log.info("Metadata extracted");

            // Extract apply URL
            extractApplyUrl(driver, job);
            log.info("Apply URL extracted");

            // Extract job description sections
            extractJobContent(driver, job);
            log.info("Content extracted");

            log.debug("Scraped job: {}", job);

        } catch (Exception e) {
            log.error("Error scraping job {}: {}", url, e.getMessage());
        }

        return job;
    }

    /**
     * Scrapes multiple jobs using a shared WebDriver.
     */
    public List<Job> scrapeJobs(List<String> urls) {
        List<Job> jobs = new ArrayList<>();
        WebDriver driver = config.createWebDriver();

        try {
            for (int i = 0; i < urls.size(); i++) {
                String url = urls.get(i);
                log.info("Scraping job {}/{}: {}", i + 1, urls.size(), url);

                Job job = scrapeJob(url, driver);
                if (job.getTitle() != null) {
                    jobs.add(job);
                }

                // Rate limiting
                if (i < urls.size() - 1) {
                    Thread.sleep(config.getRequestDelay());
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("Scraping interrupted");
        } finally {
            driver.quit();
        }

        return jobs;
    }

    private void extractMetadata(WebDriver driver, Job job) {
        try {
            // Try to find metadata in list format - be more specific to avoid description
            // lists
            // Usually metadata is at the top in a ul/li structure
            List<WebElement> metaItems = driver.findElements(
                    By.cssSelector(".job-header li, .job-meta li, .job-info li"));

            for (WebElement item : metaItems) {
                String text = item.getText().trim();
                categorizeMetadata(text, job);
            }

            // Also try data attributes or specific spans
            List<WebElement> dataSpans = driver.findElements(
                    By.cssSelector("[data-field], .location, .department, .job-type"));

            for (WebElement span : dataSpans) {
                String field = span.getAttribute("data-field");
                String text = span.getText().trim();

                if (field != null) {
                    switch (field.toLowerCase()) {
                        case "location" -> job.setLocation(text);
                        case "department" -> job.setDepartment(text);
                        case "type" -> job.setEmploymentType(text);
                    }
                } else {
                    categorizeMetadata(text, job);
                }
            }

            // Try to extract from page content patterns (REQ-XXXXXXX format for date)
            String pageText = driver.findElement(By.tagName("body")).getText();

            // Look for posting date pattern like "09/02/2026"
            Pattern datePattern = Pattern.compile("(\\d{2}/\\d{2}/\\d{4})");
            Matcher dateMatcher = datePattern.matcher(pageText);
            if (dateMatcher.find() && job.getDatePosted() == null) {
                job.setDatePosted(parseDate(dateMatcher.group(1)));
            }

        } catch (Exception e) {
            log.debug("Error extracting metadata: {}", e.getMessage());
        }
    }

    private void categorizeMetadata(String text, Job job) {
        if (text.isEmpty())
            return;

        String lower = text.toLowerCase();

        // Location patterns
        if (lower.contains("sydney") || lower.contains("amsterdam") || lower.contains("warsaw") ||
                lower.contains("singapore") || lower.contains("manila") || lower.contains(",") &&
                        (lower.contains("australia") || lower.contains("netherlands") || lower.contains("poland"))) {
            if (job.getLocation() == null)
                job.setLocation(text);
        }
        // Department patterns
        else if (lower.contains("tech") || lower.contains("finance") || lower.contains("risk") ||
                lower.contains("marketing") || lower.contains("communications") || lower.contains("hr") ||
                lower.contains("compliance") || lower.contains("operations")) {
            if (job.getDepartment() == null)
                job.setDepartment(text);
        }
        // Employment type
        else if (lower.contains("full time") || lower.contains("full-time") ||
                lower.contains("part time") || lower.contains("part-time") ||
                lower.contains("contract") || lower.contains("permanent")) {
            if (job.getEmploymentType() == null)
                job.setEmploymentType(text);
        }
        // Experience level
        else if (lower.contains("professional") || lower.contains("student") ||
                lower.contains("graduate") || lower.contains("senior") ||
                lower.contains("junior") || lower.contains("intern")) {
            if (job.getExperienceLevel() == null)
                job.setExperienceLevel(text);
        }
        // Entity
        else if (lower.contains("ing bank") || lower.contains("ing")) {
            if (job.getEntity() == null)
                job.setEntity(text);
        }
    }

    private void extractApplyUrl(WebDriver driver, Job job) {
        try {
            List<WebElement> applyLinks = driver.findElements(
                    By.cssSelector("a[href*='apply'], a[href*='workday'], button.apply"));

            for (WebElement link : applyLinks) {
                String href = link.getAttribute("href");
                if (href != null && (href.contains("apply") || href.contains("workday"))) {
                    job.setApplyUrl(href);
                    break;
                }
            }
        } catch (Exception e) {
            log.debug("Error extracting apply URL: {}", e.getMessage());
        }
    }

    private void extractJobContent(WebDriver driver, Job job) {
        try {
            StringBuilder description = new StringBuilder();
            List<String> responsibilities = new ArrayList<>();
            List<String> requirements = new ArrayList<>();
            List<String> benefits = new ArrayList<>();

            // Get all content sections
            List<WebElement> sections = driver.findElements(
                    By.cssSelector("article, .job-description, .job-content, [class*='content']"));

            if (sections.isEmpty()) {
                sections = driver.findElements(By.cssSelector("main, .main-content"));
            }

            String currentSection = "description";
            boolean foundContent = false;

            for (WebElement section : sections) {
                List<WebElement> elements = section.findElements(
                        By.cssSelector("h2, h3, h4, p, li"));

                if (!elements.isEmpty())
                    foundContent = true;

                for (WebElement element : elements) {
                    String tagName = element.getTagName().toLowerCase();
                    String text = element.getText().trim();

                    if (text.isEmpty())
                        continue;

                    // Detect section headers
                    if (tagName.startsWith("h")) {
                        String headerLower = text.toLowerCase();
                        if (headerLower.contains("what you'll do") || headerLower.contains("responsibilities") ||
                                headerLower.contains("your role") || headerLower.contains("key responsibilities")) {
                            currentSection = "responsibilities";
                        } else if (headerLower.contains("what we're looking") || headerLower.contains("requirements") ||
                                headerLower.contains("qualifications") || headerLower.contains("skills")) {
                            currentSection = "requirements";
                        } else if (headerLower.contains("benefits") || headerLower.contains("what's in it for you") ||
                                headerLower.contains("we offer") || headerLower.contains("perks")) {
                            currentSection = "benefits";
                        } else if (headerLower.contains("about")) {
                            currentSection = "description";
                        }
                        continue;
                    }

                    // Add content to appropriate section
                    switch (currentSection) {
                        case "responsibilities" -> {
                            if (tagName.equals("li"))
                                responsibilities.add(text);
                        }
                        case "requirements" -> {
                            if (tagName.equals("li"))
                                requirements.add(text);
                        }
                        case "benefits" -> {
                            if (tagName.equals("li"))
                                benefits.add(text);
                        }
                        default -> {
                            if (tagName.equals("p"))
                                description.append(text).append("\n\n");
                        }
                    }
                }
            }

            // Fallback: If no content found, search for the biggest text block
            if (!foundContent || (description.length() < 100 && responsibilities.isEmpty())) {
                log.info("Structured content not found, using fallback extraction");
                try {
                    WebElement main = driver.findElement(By.tagName("main"));
                    if (main != null) {
                        job.setDescription(main.getText());
                    } else {
                        job.setDescription(driver.findElement(By.tagName("body")).getText());
                    }
                } catch (Exception e) {
                    // ignore
                }
            } else {
                if (!description.isEmpty())
                    job.setDescription(description.toString().trim());
                if (!responsibilities.isEmpty())
                    job.setResponsibilities(responsibilities);
                if (!requirements.isEmpty())
                    job.setRequirements(requirements);
                if (!benefits.isEmpty())
                    job.setBenefits(benefits);
            }

        } catch (Exception e) {
            log.debug("Error extracting job content: {}", e.getMessage());
        }
    }

    private String extractText(WebDriver driver, String selector) {
        try {
            WebElement element = driver.findElement(By.cssSelector(selector));
            return element.getText().trim();
        } catch (NoSuchElementException e) {
            return null;
        }
    }

    private LocalDate parseDate(String dateStr) {
        if (dateStr == null || dateStr.isEmpty())
            return null;

        for (DateTimeFormatter formatter : DATE_FORMATTERS) {
            try {
                return LocalDate.parse(dateStr, formatter);
            } catch (DateTimeParseException e) {
                // Try next formatter
            }
        }
        return null;
    }
}
