package com.ing.parser.config;

import io.github.bonigarcia.wdm.WebDriverManager;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * Configuration for Selenium WebDriver.
 */
@Configuration
public class ScraperConfig {

    @Value("${scraper.headless:true}")
    private boolean headless;

    @Value("${scraper.page-load-timeout:30}")
    private int pageLoadTimeout;

    @Value("${scraper.implicit-wait:2}")
    private int implicitWait;

    @Value("${scraper.request-delay:1000}")
    private long requestDelay;

    /**
     * Creates a Chrome WebDriver instance.
     * Note: This is a prototype scope - each call creates a new driver.
     * Remember to quit the driver when done.
     */
    public WebDriver createWebDriver() {
        WebDriverManager.chromedriver().setup();

        ChromeOptions options = new ChromeOptions();
        if (headless) {
            options.addArguments("--headless=new");
        }
        options.addArguments("--no-sandbox");
        options.addArguments("--disable-dev-shm-usage");
        options.addArguments("--disable-gpu");
        options.addArguments("--window-size=1920,1080");
        options.addArguments("--disable-blink-features=AutomationControlled");
        options.addArguments("--remote-allow-origins=*");
        options.addArguments("--ignore-certificate-errors");
        options.addArguments(
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");

        ChromeDriver driver = new ChromeDriver(options);
        driver.manage().timeouts().pageLoadTimeout(Duration.ofSeconds(pageLoadTimeout));
        driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(implicitWait));

        return driver;
    }

    public long getRequestDelay() {
        return requestDelay;
    }

    public int getPageLoadTimeout() {
        return pageLoadTimeout;
    }
}
