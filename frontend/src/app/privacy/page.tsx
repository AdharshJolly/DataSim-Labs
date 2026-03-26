import { LegalPageTemplate } from "@/components/layout/legal-page-template";

const sections = [
  {
    id: "information-we-collect",
    title: "Information We Collect",
    paragraphs: [
      "We collect account information such as your email address and authentication metadata required to operate secure sign-in and session management.",
      "When you use dataset generation workflows, we store dataset configurations, generation parameters, and related operational metadata so your projects can be previewed, resumed, generated, and downloaded reliably.",
      "We also process technical telemetry such as request timing, service health events, and security logs to detect abuse, monitor platform stability, and investigate incidents.",
    ],
  },
  {
    id: "how-we-use-information",
    title: "How We Use Information",
    paragraphs: [
      "We use collected information to deliver core platform functionality, including account authentication, dataset orchestration, async job processing, artifact storage, and download access.",
      "Operational and diagnostic data is used to improve reliability, troubleshoot errors, enforce security controls, and maintain service performance for all users.",
      "We do not use your account or dataset configuration data for advertising purposes, and we do not sell personal information to third parties.",
    ],
  },
  {
    id: "cookies-and-session-security",
    title: "Cookies and Session Security",
    paragraphs: [
      "DataSim Lab uses essential authentication cookies for secure session handling. These cookies are configured as HttpOnly and are not accessible through client-side scripts.",
      "In production environments, authentication cookies are configured with secure transport settings so they are transmitted only over HTTPS.",
      "Session cookies are used only for authentication continuity and access control. For more detail on categories and behavior, review our Cookie Policy.",
    ],
  },
  {
    id: "data-retention",
    title: "Data Retention",
    paragraphs: [
      "We retain account and platform records for as long as needed to provide services, satisfy legal obligations, resolve disputes, and enforce agreements.",
      "Generated artifacts and operational logs may be retained for limited periods based on system retention policies and infrastructure constraints.",
      "When retention is no longer necessary, data is deleted or de-identified according to operational and legal requirements.",
    ],
  },
  {
    id: "sharing-and-disclosures",
    title: "Sharing and Disclosures",
    paragraphs: [
      "We share data with infrastructure and service providers only as necessary to operate the platform, including hosting, database, caching, storage, and monitoring services.",
      "Service providers process data under contractual obligations and are expected to use appropriate security safeguards.",
      "We may disclose information when required by law, legal process, or to protect the rights, safety, and security of users, the platform, or the public.",
    ],
  },
  {
    id: "your-rights",
    title: "Your Rights and Choices",
    paragraphs: [
      "Depending on your jurisdiction, you may have rights to access, correct, delete, or restrict processing of your personal information.",
      "You may also request information about the categories of data we process and the purposes for which it is used.",
      "To submit privacy-related requests, contact your administrator or support contact listed by your deployment owner.",
    ],
  },
  {
    id: "changes",
    title: "Policy Changes",
    paragraphs: [
      "We may update this Privacy Policy to reflect changes in product functionality, legal requirements, or security practices.",
      "When material updates are made, we will update the last-updated date on this page and provide additional notice where required.",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <LegalPageTemplate
      eyebrow="Legal"
      title="Privacy Policy"
      summary="This Privacy Policy explains how DataSim Lab collects, uses, stores, and protects information when you use the platform, including authentication, dataset generation workflows, and operational infrastructure."
      updatedAt="March 26, 2026"
      scope={[
        "Applies to web app usage, account authentication, and generated dataset workflows.",
        "Covers product operations, security controls, and service reliability activities.",
        "Intended as a deployable baseline policy and should be reviewed with legal counsel for jurisdiction-specific compliance.",
      ]}
      sections={sections}
    />
  );
}
