<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:import href="factur-x-1.09/4_Factur-X_1.09_EXTENDED/_XSLT_EXTENDED/FACTUR-X_EXTENDED.xslt" />
<!-- The purpose of this XSLT is to expose messages with a human-readable path. -->
  <xsl:template match="*" mode="schematron-select-full-path">
    <xsl:apply-templates mode="schematron-get-full-path-3" select="." />
  </xsl:template>
</xsl:stylesheet>