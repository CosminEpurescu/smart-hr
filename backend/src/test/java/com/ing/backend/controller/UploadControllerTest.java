package com.ing.backend.controller;

import com.mongodb.client.MongoClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ComponentScan("com.ing.backend")
class UploadControllerTest {

    @MockitoBean
    private MongoClient mongoClient;

    @Autowired
    private UploadController uploadController;

    @Test
    public void checkAop() {
        uploadController.resumeUpload(UUID.randomUUID(), null, null);
    }
}