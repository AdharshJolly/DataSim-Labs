import { LegalPageTemplate } from "@/components/layout/legal-page-template";

const sections = [
  {
    id: "what-are-cookies",
    title: "What Are Cookies",
    paragraphs: [
      "Cookies are small text files stored by your browser that help websites maintain sessions, remember preferences, and improve reliability.",
      "DataSim Lab primarily uses cookies for secure authentication and session continuity within protected areas of the platform.",
    ],
  },
  {
    id: "cookie-categories",
    title: "Cookie Categories We Use",
    paragraphs: [
      "Essential authentication cookies: Required for login, account session state, and access to protected routes.",
      "Security cookies: Used to maintain secure session handling and reduce unauthorized access risks.",
      "We do not currently use advertising cookies in the core product experience.",
    ],
  },
  {
    id: "authentication-cookies",
    title: "Authentication Cookie Details",
    paragraphs: [
      "Authentication cookies are configured with HttpOnly attributes so they are not accessible through client-side JavaScript.",
      "In production, cookies are configured with secure transport controls to support HTTPS-only transmission.",
      "SameSite configuration may vary by deployment architecture, especially when frontend and backend are deployed on different domains.",
    ],
  },
  {
    id: "duration-and-retention",
    title: "Cookie Duration and Retention",
    paragraphs: [
      "Some cookies are session-based and expire when your browser session ends, while others are short-lived persistent cookies for refresh and continuity behavior.",
      "Cookie lifetime is tied to authentication policy and may be updated for security hardening or operational requirements.",
    ],
  },
  {
    id: "managing-cookies",
    title: "Managing Cookies",
    paragraphs: [
      "Most browsers let you block or delete cookies through privacy settings. Disabling essential cookies may prevent login and core platform functionality.",
      "If you use strict browser controls or privacy extensions, some authenticated workflows may not behave as expected.",
    ],
  },
  {
    id: "third-party-services",
    title: "Third-Party Services",
    paragraphs: [
      "Platform infrastructure may rely on third-party hosting, caching, storage, and observability providers that support service delivery.",
      "Where third-party cookies are present through embedded services, they are governed by the applicable provider policy.",
    ],
  },
  {
    id: "changes-to-cookie-policy",
    title: "Changes to This Policy",
    paragraphs: [
      "We may update this Cookie Policy to reflect product changes, legal requirements, or security enhancements.",
      "When updates are made, the policy date on this page is revised so you can track the latest version.",
    ],
  },
];

export default function CookiesPage() {
  return (
    <LegalPageTemplate
      eyebrow="Legal"
      title="Cookie Policy"
      summary="This Cookie Policy explains how DataSim Lab uses cookies and related storage mechanisms for authentication, security, and service continuity."
      updatedAt="March 26, 2026"
      scope={[
        "Covers cookies used by the web application and authenticated workflows.",
        "Focuses on essential and security-related cookie behavior.",
        "Should be aligned with jurisdiction-specific consent requirements for production deployments.",
      ]}
      sections={sections}
    />
  );
}
