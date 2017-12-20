#!/usr/bin/env groovy

pipeline {
    agent any

    options {
        disableConcurrentBuilds()
    }

    stages {
        stage("Announcement") {
            steps {
                sh "pipeline-notification STARTED SUCCESS"
            }
        }

        stage("Build") {
            when {
                branch "production"
            }

            steps {
                sshagent(["f4f6a0a8-c2ae-4f7e-9bf1-869831034fad"]) {
                    sh "ansible-playbook -l medley ansible/install.yml"
                }
            }
        }
    }

    post {
        success {
            sh "pipeline-notification FINALIZED SUCCESS"
        }

        failure {
            sh "pipeline-notification FINALIZED FAILURE"
        }
    }
}
