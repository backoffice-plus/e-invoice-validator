<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:import href="factur-x-1.07.2/1.%20Factur-X_1.07.2_BASICWL/_XSLT_BASIC-WL/FACTUR-X_BASIC-WL.xslt" />
  <!-- we use a human-readable path -->
  <xsl:template match="*" mode="schematron-select-full-path">
    <xsl:apply-templates mode="schematron-get-full-path-3" select="." />
  </xsl:template>
</xsl:stylesheet>