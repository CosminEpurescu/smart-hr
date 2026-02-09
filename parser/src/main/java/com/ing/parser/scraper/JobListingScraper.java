package com.ing.parser.scraper;

import com.ing.parser.config.ScraperConfig;
import org.openqa.selenium.*;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Scrapes job listing URLs from ING Careers search page with pagination.
 */
@Service
public class JobListingScraper {

    private static final Logger log = LoggerFactory.getLogger(JobListingScraper.class);
    private static final String SEARCH_URL = "https://careers.ing.com/en/search-jobs";

    private final ScraperConfig config;

    public JobListingScraper(ScraperConfig config) {
        this.config = config;
    }

    /**
     * Scrapes all job URLs from the ING Careers search page.
     * Handles "Load More" pagination to get all jobs.
     * 
     * @param limit Maximum number of jobs to scrape (0 = unlimited)
     * @return List of job URLs
     */
    public List<String> scrapeJobUrls(int limit) {
        Set<String> jobUrls = new HashSet<>();
        WebDriver driver = config.createWebDriver();

        try {
            log.info("Navigating to job search page: {}", SEARCH_URL);
            driver.get(SEARCH_URL);

            // Wait for job listings to load
            WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(config.getPageLoadTimeout()));
            wait.until(ExpectedConditions.presenceOfElementLocated(
                    By.cssSelector("a[href*='/job/']")));

            // Accept cookies if present
            acceptCookiesIfPresent(driver);

            int previousCount = 0;
            int noNewJobsCounter = 0;

            while (limit == 0 || jobUrls.size() < limit) {
                // Extract current job URLs
                List<WebElement> jobLinks = driver.findElements(
                        By.cssSelector("a[href*='/en/job/']"));

                for (WebElement link : jobLinks) {
                    String href = link.getAttribute("href");
                    if (href != null && href.contains("/job/") && !href.contains("job_location")) {
                        jobUrls.add(href);
                        if (limit > 0 && jobUrls.size() >= limit) {
                            break;
                        }
                    }
                }

                log.info("Found {} unique job URLs so far", jobUrls.size());

                // Check if we got new jobs
                if (jobUrls.size() == previousCount) {
                    noNewJobsCounter++;
                    if (noNewJobsCounter >= 3) {
                        log.info("No new jobs found after 3 attempts, stopping pagination");
                        break;
                    }
                } else {
                    noNewJobsCounter = 0;
                }
                previousCount = jobUrls.size();

                // Try to load more jobs
                if (!clickLoadMore(driver, wait)) {
                    log.info("No more 'Load More' button, pagination complete");
                    break;
                }

                // Wait for new jobs to load
                Thread.sleep(config.getRequestDelay());
            }

            log.info("Scraped {} total job URLs", jobUrls.size());

        } catch (Exception e) {
            log.error("Error scraping job listings: {}", e.getMessage(), e);
        } finally {
            driver.quit();
        }

        return new ArrayList<>(jobUrls);
    }

    private void acceptCookiesIfPresent(WebDriver driver) {
        try {
            WebElement cookieButton = driver.findElement(
                    By.cssSelector("button[id*='accept'], button[class*='accept'], button[class*='cookie']"));
            if (cookieButton.isDisplayed()) {
                cookieButton.click();
                log.info("Accepted cookies");
                Thread.sleep(500);
            }
        } catch (NoSuchElementException | InterruptedException e) {
            // Cookie banner not present, that's fine
        }
    }

    private boolean clickLoadMore(WebDriver driver, WebDriverWait wait) {
        try {
            // Scroll to bottom first
            ((JavascriptExecutor) driver).executeScript(
                    "window.scrollTo(0, document.body.scrollHeight);");
            Thread.sleep(500);

            // Look for "Load More" or "Show More" button
            List<WebElement> loadMoreButtons = driver.findElements(
                    By.cssSelector("button[class*='load-more'], button[class*='show-more'], " +
                            "a[class*='load-more'], button:contains('Load'), button:contains('More')"));

            // Also try by text content
            if (loadMoreButtons.isEmpty()) {
                loadMoreButtons = driver.findElements(By.xpath(
                        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')] | "
                                +
                                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')] | "
                                +
                                "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'load more')]"));
            }

            for (WebElement button : loadMoreButtons) {
                if (button.isDisplayed() && button.isEnabled()) {
                    try {
                        ((JavascriptExecutor) driver).executeScript(
                                "arguments[0].scrollIntoView(true);", button);
                        Thread.sleep(300);
                        button.click();
                        log.debug("Clicked 'Load More' button");
                        return true;
                    } catch (ElementClickInterceptedException e) {
                        // Try JS click
                        ((JavascriptExecutor) driver).executeScript(
                                "arguments[0].click();", button);
                        return true;
                    }
                }
            }

            // Try infinite scroll as fallback
            long beforeHeight = (Long) ((JavascriptExecutor) driver).executeScript(
                    "return document.body.scrollHeight");
            ((JavascriptExecutor) driver).executeScript(
                    "window.scrollTo(0, document.body.scrollHeight);");
            Thread.sleep(1500);
            long afterHeight = (Long) ((JavascriptExecutor) driver).executeScript(
                    "return document.body.scrollHeight");

            return afterHeight > beforeHeight;

        } catch (Exception e) {
            log.debug("Could not find or click 'Load More': {}", e.getMessage());
            return false;
        }
    }
}
