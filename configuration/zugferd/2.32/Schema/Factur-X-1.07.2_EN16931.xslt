<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:import href="factur-x-1.07.2/3.%20Factur-X_1.07.2_EN16931/_XSLT_EN16931/FACTUR-X_EN16931.xslt" />
  <!-- we use a human-readable path -->
  <xsl:template match="*" mode="schematron-select-full-path">
    <xsl:apply-templates mode="schematron-get-full-path-3" select="." />
  </xsl:template>
</xsl:stylesheet>