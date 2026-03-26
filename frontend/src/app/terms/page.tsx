import { LegalPageTemplate } from "@/components/layout/legal-page-template";

const sections = [
  {
    id: "acceptance-of-terms",
    title: "Acceptance of Terms",
    paragraphs: [
      "By accessing or using DataSim Lab, you agree to be bound by these Terms of Service and any applicable policies referenced within them.",
      "If you are using the platform on behalf of an organization, you represent that you are authorized to accept these terms for that organization.",
      "If you do not agree to these terms, you must stop using the service.",
    ],
  },
  {
    id: "service-description",
    title: "Service Description",
    paragraphs: [
      "DataSim Lab provides synthetic dataset design, preview, and generation capabilities, including configurable schema constraints, export workflows, and asynchronous processing features.",
      "Service availability, features, and performance characteristics may evolve over time as part of normal maintenance, upgrades, and security improvements.",
    ],
  },
  {
    id: "accounts-and-security",
    title: "Accounts and Security",
    paragraphs: [
      "You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account.",
      "You agree to notify the service operator promptly of unauthorized account access, credential compromise, or suspected security incidents.",
      "We may suspend or restrict accounts that present security risk, abuse behavior, or violations of these terms.",
    ],
  },
  {
    id: "acceptable-use",
    title: "Acceptable Use",
    paragraphs: [
      "You agree not to misuse the service, attempt unauthorized access, reverse engineer protected systems, interfere with platform availability, or upload malicious content.",
      "You are solely responsible for ensuring your use of generated datasets complies with applicable law, contractual obligations, and internal governance requirements.",
      "Use of the platform for unlawful, harmful, or abusive activity is prohibited and may result in immediate termination.",
    ],
  },
  {
    id: "intellectual-property",
    title: "Intellectual Property",
    paragraphs: [
      "The platform, source materials, branding, and service components are protected by applicable intellectual property laws and remain the property of their respective owners.",
      "Except for rights explicitly granted in these terms, no license is provided to copy, distribute, or create derivative works from protected service assets.",
    ],
  },
  {
    id: "data-and-content",
    title: "Data and Content Responsibility",
    paragraphs: [
      "You retain responsibility for the data, prompts, and configuration inputs you provide, and for outputs you generate through the platform.",
      "You represent that you have the rights and permissions necessary to submit input data and use generated outputs for your intended purposes.",
    ],
  },
  {
    id: "disclaimers-and-liability",
    title: "Disclaimers and Liability",
    paragraphs: [
      "The service is provided on an as-available basis. To the maximum extent permitted by law, we disclaim warranties of merchantability, fitness for a particular purpose, and non-infringement.",
      "To the maximum extent permitted by law, we are not liable for indirect, incidental, special, consequential, or punitive damages arising from service use.",
      "Where liability cannot be excluded, it is limited to the minimum extent allowed by applicable law.",
    ],
  },
  {
    id: "termination",
    title: "Suspension and Termination",
    paragraphs: [
      "We may suspend or terminate access if these terms are violated, if required by law, or if continued service presents security or operational risk.",
      "You may stop using the platform at any time. Certain obligations that by nature should survive termination will remain in effect.",
    ],
  },
  {
    id: "governing-law",
    title: "Governing Law",
    paragraphs: [
      "These terms should be interpreted under the governing law selected by the deploying organization.",
      "Replace this section with jurisdiction-specific governing law and dispute resolution language before production legal publication.",
    ],
  },
];

export default function TermsPage() {
  return (
    <LegalPageTemplate
      eyebrow="Legal"
      title="Terms of Service"
      summary="These Terms of Service govern access to and use of DataSim Lab, including account operation, acceptable use, service limitations, and responsibilities for generated data outputs."
      updatedAt="March 26, 2026"
      scope={[
        "Applies to all users, teams, and organizations accessing the platform.",
        "Defines permitted use, restrictions, and account security responsibilities.",
        "Should be reviewed and finalized by legal counsel before public release.",
      ]}
      sections={sections}
    />
  );
}
