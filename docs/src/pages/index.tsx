import React from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import { HomepageHeader } from '../components/HomepageHeader/HomepageHeader';
import { translate } from '@docusaurus/Translate';

export default function Home(): JSX.Element {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title}`}
      description={translate({
        id: 'homepage.description',
        message: 'Code Less, Make More',
      })}
    >
      <HomepageHeader />
    </Layout>
  );
}
