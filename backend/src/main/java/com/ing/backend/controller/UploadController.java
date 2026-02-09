package com.ing.backend.controller;

import com.ing.smarthr.producer.api.ResumeUploadApi;
import com.ing.smarthr.producer.model.CVUploadResponse;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

@RestController
@RequestMapping
public class UploadController implements ResumeUploadApi {

    @Override
    public ResponseEntity<CVUploadResponse> resumeUpload(@Valid UUID requestId, @Valid MultipartFile document, String jobId) {
        return ResumeUploadApi.super.resumeUpload(requestId, document, jobId);
    }
}
