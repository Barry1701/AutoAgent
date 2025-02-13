import React from "react";
import { FaSlack, FaDiscord, FaGithub } from "react-icons/fa";
import Translate from '@docusaurus/Translate';
import "../css/footer.css";

function CustomFooter() {
  return (
    <footer className="custom-footer">
      <div className="footer-content">
        <div className="footer-icons">
          <a href="https://join.slack.com/t/metachain-workspace/shared_invite/zt-2zibtmutw-v7xOJObBf9jE2w3x7nctFQ" target="_blank" rel="noopener noreferrer">
            <FaSlack />
          </a>
          <a href="https://discord.gg/z68KRvwB" target="_blank" rel="noopener noreferrer">
            <FaDiscord />
          </a>
          <a href="https://github.com/HKUDS/MetaChain" target="_blank" rel="noopener noreferrer">
            <FaGithub />
          </a>
        </div>
        <div className="footer-bottom">
          <p>
            <Translate id="footer.copyright" values={{ year: new Date().getFullYear() }}>
              {'Copyright © {year} HKU MetaChain Team'}
            </Translate>
          </p>
        </div>
      </div>
    </footer>
  );
}

export default CustomFooter;
