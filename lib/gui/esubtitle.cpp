#include <lib/gui/esubtitle.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/gdi/grc.h>
#include <lib/gdi/font.h>
#include <lib/base/estring.h>
#include <lib/base/nconfig.h>

	/*
		ok, here's much room for improvements.
	
		first, the placing of the individual elements is sub-optimal.
		then maybe a colored background would be an option.
		....
 	*/	

eSubtitleWidget::eSubtitleStyle eSubtitleWidget::subtitleStyles[Subtitle_MAX];

eSubtitleWidget::eSubtitleWidget(eWidget *parent)
	: eWidget(parent), m_hide_subtitles_timer(eTimer::create(eApp))
{
	setBackgroundColor(gRGB(0,0,0,255));
	m_page_ok = 0;
	m_dvb_page_ok = 0;
	m_pango_page_ok = 0;
	CONNECT(m_hide_subtitles_timer->timeout, eSubtitleWidget::clearPage);
}

#define startX 50
#define paddingY 10
void eSubtitleWidget::setPage(const eDVBTeletextSubtitlePage &p)
{
	eDVBTeletextSubtitlePage newpage = p;
	m_page = p;
	m_page.clear();
	m_page_ok = 1;
	invalidate(m_visible_region);  // invalidate old visible regions
	m_visible_region.rects.clear();

	unsigned int elements = newpage.m_elements.size();
	if (elements)
	{
		int fontsize = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_fontsize", 34) * getDesktop(0)->size().width()/1280;
		int startY = size().height() - (size().height() / 3 * 1) / 2 - ((fontsize + paddingY) * elements) / 2;
		int width = size().width() - startX * 2;
		int height = size().height() - startY;
		int size_per_element = fontsize + paddingY;
		bool original_position = ePythonConfigQuery::getConfigBoolValue("config.subtitles.subtitle_original_position");
		bool rewrap = ePythonConfigQuery::getConfigBoolValue("config.subtitles.subtitle_rewrap");
		gRGB color;
		bool original_colors = false;
		switch (ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_fontcolor", 0))
		{
			default:
			case 0: /* use original teletext colors */
				color = newpage.m_elements[0].m_color;
				original_colors = true;
				break;
			case FONTCOLOR_WHITE:
				color = gRGB(255, 255, 255);
				break;
			case FONTCOLOR_YELLOW:
				color = gRGB(255, 255, 0);
				break;
			case FONTCOLOR_GREEN:
				color = gRGB(0, 255, 0);
				break;
			case FONTCOLOR_CYAN:
				color = gRGB(0, 255, 255);
				break;
			case FONTCOLOR_BLUE:
				color = gRGB(0, 0, 255);
				break;
			case FONTCOLOR_MAGNETA:
				color = gRGB(255, 0, 255);
				break;
			case FONTCOLOR_RED:
				color = gRGB(255, 0, 0);
				break;
			case FONTCOLOR_BLACK:
				color = gRGB(0, 0, 0);
				break;
		}
		color.a = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_opacity");

		int line = newpage.m_elements[0].m_source_line;
		int currentelement = 0;
		m_page.m_elements.push_back(eDVBTeletextSubtitlePageElement(color, "", line));
		for (int i=0; i<elements; ++i)
		{
			if (!m_page.m_elements[currentelement].m_text.empty())
				m_page.m_elements[currentelement].m_text += " ";
			if (original_colors && color != newpage.m_elements[i].m_color)
			{
				color = newpage.m_elements[i].m_color;
				m_page.m_elements[currentelement].m_text += (std::string)color;
			}
			if (line != newpage.m_elements[i].m_source_line)
			{
				line = newpage.m_elements[i].m_source_line;
				if (!rewrap)
				{
					m_page.m_elements.push_back(eDVBTeletextSubtitlePageElement(color, "", line));
					currentelement++;
				}
			}
			m_page.m_elements[currentelement].m_text += newpage.m_elements[i].m_text;
		}
		for (int i=0; i<m_page.m_elements.size(); i++)
		{
			eRect &area = m_page.m_elements[i].m_area;
			area.setLeft(startX);
			if (!original_position)
			{
				int lowerborder = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_position", 50);
				area.setTop(size().height() - size_per_element * (m_page.m_elements.size() - i) - lowerborder * getDesktop(0)->size().height()/720);
			}
			else
				area.setTop(size_per_element * i + startY);
			area.setWidth(width);
			area.setHeight(size_per_element);
			m_visible_region.rects.push_back(area);
		}
	}
	m_hide_subtitles_timer->start(7500, true);
	invalidate(m_visible_region);  // invalidate new regions
}

void eSubtitleWidget::setPage(const eDVBSubtitlePage &p)
{
	eDebug("setPage");
	m_dvb_page = p;
	invalidate(m_visible_region);  // invalidate old visible regions
	m_visible_region.rects.clear();
	int line = 0;
	bool original_position = ePythonConfigQuery::getConfigBoolValue("config.subtitles.subtitle_original_position");
	for (std::list<eDVBSubtitleRegion>::iterator it(m_dvb_page.m_regions.begin()); it != m_dvb_page.m_regions.end(); ++it)
	{
		if (!original_position)
		{
			int lines = m_dvb_page.m_regions.size();
			int lowerborder = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_position", -1);
			if (lowerborder >= 0)
			{
				it->m_position = ePoint(it->m_position.x(), p.m_display_size.height() - (lines - line) * it->m_pixmap->size().height() - lowerborder);
			}
			line++;
		}
		eDebug("add %d %d %d %d", it->m_position.x(), it->m_position.y(), it->m_pixmap->size().width(), it->m_pixmap->size().height());
		eDebug("disp width %d, disp height %d", p.m_display_size.width(), p.m_display_size.height());
		eRect r = eRect(it->m_position, it->m_pixmap->size());
		r.scale(size().width(), p.m_display_size.width(), size().height(), p.m_display_size.height());
		m_visible_region.rects.push_back(r);
	}
	m_dvb_page_ok = 1;
	m_hide_subtitles_timer->start(7500, true);
	invalidate(m_visible_region);  // invalidate new regions
}

void eSubtitleWidget::setPage(const ePangoSubtitlePage &p)
{
	m_pango_page = p;
	m_pango_page_ok = 1;
	invalidate(m_visible_region);  // invalidate old visible regions
	m_visible_region.rects.clear();

	bool rewrap_enabled = ePythonConfigQuery::getConfigBoolValue("config.subtitles.subtitle_rewrap");
	bool colourise_dialogs_enabled = ePythonConfigQuery::getConfigBoolValue("config.subtitles.colourise_dialogs");
	bool original_position = ePythonConfigQuery::getConfigBoolValue("config.subtitles.subtitle_original_position");

	int elements = m_pango_page.m_elements.size();

	if(rewrap_enabled | colourise_dialogs_enabled)
	{
		size_t ix, colourise_dialogs_current = 0;
		std::vector<std::string> colourise_dialogs_colours;
		std::string replacement;
		std::string alignmentValue;
		ePythonConfigQuery::getConfigValue("config.subtitles.subtitle_alignment", alignmentValue);
		bool alignment_center = (alignmentValue == "center");

		if(colourise_dialogs_enabled)
		{
			colourise_dialogs_colours.push_back((std::string)gRGB(0xff, 0xff, 0x00));	// yellow
			colourise_dialogs_colours.push_back((std::string)gRGB(0x00, 0xff, 0xff));	// cyan
			colourise_dialogs_colours.push_back((std::string)gRGB(0xff, 0x00, 0xff));	// magenta
			colourise_dialogs_colours.push_back((std::string)gRGB(0x00, 0xff, 0x00));	// green
			colourise_dialogs_colours.push_back((std::string)gRGB(0xff, 0xaa, 0xaa));	// light red
			colourise_dialogs_colours.push_back((std::string)gRGB(0xaa, 0xaa, 0xff));	// light blue
		}

		for (int i=0; i<elements; ++i)
		{
			std::string& line = m_pango_page.m_elements[i].m_pango_line;

			for (ix = 0; ix < line.length(); ix++)
			{
				if(rewrap_enabled && !line.compare(ix, 1, "\n"))
					line.replace(ix, 1, " ");

				if(colourise_dialogs_enabled && !line.compare(ix, 2, "- "))
				{
					/* workaround for rendering fault when colouring is enabled, rewrap is off and alignment is center */
					replacement = std::string((!rewrap_enabled && alignment_center) ? "  " : "") + colourise_dialogs_colours.at(colourise_dialogs_current);

					line.replace(ix, 2, replacement);
					colourise_dialogs_current++;

					if(colourise_dialogs_current >= colourise_dialogs_colours.size())
						colourise_dialogs_current = 0;
				}
			}
		}
	}

	if (elements)
	{
		int startY = elements > 1
			? size().height() / 2
			: size().height() / 3 * 2;
		int width = size().width() - startX * 2;
		int height = size().height() - startY;
		int size_per_element = height / (elements ? elements : 1);
		for (int i=0; i<elements; ++i)
		{
			eRect &area = m_pango_page.m_elements[i].m_area;
			area.setLeft(startX);
			if (!original_position)
			{
				int lowerborder = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_position", 50);
				if (lowerborder == 0)
					lowerborder -= 100 * getDesktop(0)->size().height()/720;
				else if (lowerborder == 50)
					lowerborder -= 50 * getDesktop(0)->size().height()/720;
				area.setTop(size_per_element * i + startY - lowerborder);
			}
			else
				area.setTop(size_per_element * i + startY);
			area.setWidth(width);
			area.setHeight(size_per_element);
			m_visible_region.rects.push_back(area);
		}
	}
	int timeout_ms = m_pango_page.m_timeout;
	m_hide_subtitles_timer->start(timeout_ms, true);
	invalidate(m_visible_region);  // invalidate new regions
}

void eSubtitleWidget::clearPage()
{
	eDebug("subtitle timeout... hide");
	m_page_ok = 0;
	m_dvb_page_ok = 0;
	m_pango_page_ok = 0;
	invalidate(m_visible_region);
	m_visible_region.rects.clear();
}

void eSubtitleWidget::setPixmap(ePtr<gPixmap> &pixmap, gRegion changed, eRect pixmap_dest)
{
	m_pixmap = pixmap;
	m_pixmap_dest = pixmap_dest; /* this is in a virtual 720x576 cage */
	
		/* incoming "changed" regions are relative to the physical pixmap area, so they have to be scaled to the virtual pixmap area, then to the screen */
	changed.scale(m_pixmap_dest.width(), 720, m_pixmap_dest.height(), 576);
	changed.moveBy(ePoint(m_pixmap_dest.x(), m_pixmap_dest.y()));

	if (pixmap->size().width() && pixmap->size().height())
		changed.scale(size().width(), pixmap->size().width(), size().height(), pixmap->size().height());
	
	invalidate(changed);
}

int eSubtitleWidget::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;
		gPainter &painter = *(gPainter*)data2;

		getStyle(style);
		eWidget::event(event, data, data2);

		std::string alignmentValue;
		int rt_halignment_flag;
		ePythonConfigQuery::getConfigValue("config.subtitles.subtitle_alignment", alignmentValue);
		if (alignmentValue == "right")
			rt_halignment_flag = gPainter::RT_HALIGN_RIGHT;
		else if (alignmentValue == "left")
			rt_halignment_flag = gPainter::RT_HALIGN_LEFT;
		else
			rt_halignment_flag = gPainter::RT_HALIGN_CENTER;

		int fontsize = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_fontsize", 34) * getDesktop(0)->size().width()/1280;
		int edgestyle = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_edgestyle");
		int borderwidth = (edgestyle == FONTSTYLE_UNIFORM) ? ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_edgestyle_level") : 0;
		gRGB bordercolor = gRGB();
		bool original_colors = false;

		if (m_pixmap)
		{
			eRect r = m_pixmap_dest;
			r.scale(size().width(), 720, size().height(), 576);
			painter.blitScale(m_pixmap, r);
		} else if (m_page_ok)
		{
			int elements = m_page.m_elements.size();

			subtitleStyles[Subtitle_TTX].font->pointSize = fontsize;

			painter.setFont(subtitleStyles[Subtitle_TTX].font);
			for (int i=0; i<elements; ++i)
			{
				eDVBTeletextSubtitlePageElement &element = m_page.m_elements[i];
				eRect &area = element.m_area;
				gRGB fontcolor = (!subtitleStyles[Subtitle_TTX].have_foreground_color) ? element.m_color : subtitleStyles[Subtitle_TTX].foreground_color;
				int bg_r, bg_g, bg_b, bg_a;
				if (ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_bgopacity") < 0xFF)
				{
					eTextPara *para = new eTextPara(area);
					para->setFont(subtitleStyles[Subtitle_TTX].font);
					para->renderString(element.m_text.c_str(), RS_WRAP);

					eRect bgbox = para->getBoundBox();
					int bgboxWidth = bgbox.width();
					int bgboxHeight = bgbox.height();
					if (alignmentValue == "left")
						bgbox.setLeft(area.left() - paddingY - borderwidth);
					else if (alignmentValue == "right")
						bgbox.setLeft(area.left() + area.width() - bgboxWidth - paddingY - borderwidth);
					else
						bgbox.setLeft(area.left() + area.width() / 2 - bgboxWidth / 2 - paddingY - borderwidth);
					bgbox.setTop(area.top());
					bgbox.setWidth(bgboxWidth + paddingY * 2 + borderwidth * 2);
					bgbox.setHeight(area.height());

					switch (ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_bgcolor", 0))
					{
						case BGCOLOR_WHITE:
							bg_r = 255;
							bg_g = 255;
							bg_b = 255;
							break;
						case BGCOLOR_YELLOW:
							bg_r = 255;
							bg_g = 255;
							bg_b = 0;
							break;
						case BGCOLOR_GREEN:
							bg_r = 0;
							bg_g = 255;
							bg_b = 0;
							break;
						case BGCOLOR_CYAN:
							bg_r = 0;
							bg_g = 255;
							bg_b = 255;
							break;
						case BGCOLOR_BLUE:
							bg_r = 0;
							bg_g = 0;
							bg_b = 255;
							break;
						case BGCOLOR_MAGNETA:
							bg_r = 255;
							bg_g = 0;
							bg_b = 255;
							break;
						case BGCOLOR_RED:
							bg_r = 255;
							bg_g = 0;
							bg_b = 0;
							break;
						case BGCOLOR_BLACK:
						default:
							bg_r = 0;
							bg_g = 0;
							bg_b = 0;
							break;
					}
					bg_a = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_bgopacity", 0);

					painter.setForegroundColor(gRGB(bg_r, bg_g, bg_b, bg_a));
					painter.fill(bgbox);
				}

				int offset = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_edgestyle_level", 3);
				switch(edgestyle)
				{
					default:
					case FONTSTYLE_NONE:
						offset = 0;
						borderwidth = 0;
						break;
					case FONTSTYLE_RAISED:
					{
						eRect shadow = area;
						ePoint shadow_offset = ePoint(-offset, -offset);
						shadow.moveBy(shadow_offset);
						painter.setForegroundColor(subtitleStyles[Subtitle_TTX].shadow_color);
						painter.renderText(shadow, element.m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|rt_halignment_flag);
					}
						break;
					case FONTSTYLE_DEPRESSED:
					{
						eRect shadow = area;
						ePoint shadow_offset = ePoint(offset, offset);
						shadow.moveBy(shadow_offset);
						painter.setForegroundColor(subtitleStyles[Subtitle_TTX].shadow_color);
						painter.renderText(shadow, element.m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|rt_halignment_flag);
					}
						break;
					case FONTSTYLE_UNIFORM:
					{
						if (borderwidth > 0)
						{
							if (fontcolor.r == 0 && fontcolor.g == 0 && fontcolor.b == 0)
							{
								gRGB tmp_border_white = gRGB(255,255,255);
								bordercolor = tmp_border_white;
							}
							else if (bg_r == 0 && bg_g == 0 && bg_b == 0)
							{
								borderwidth = 0;
							}
						}
					}
						break;
				}

				if ( !subtitleStyles[Subtitle_TTX].have_foreground_color )
					painter.setForegroundColor(element.m_color);
				else
					painter.setForegroundColor(subtitleStyles[Subtitle_TTX].foreground_color);
				painter.renderText(area, element.m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|rt_halignment_flag, bordercolor, borderwidth);
			}
		}
		else if (m_pango_page_ok)
		{
			int elements = m_pango_page.m_elements.size();
			subfont_t face;

			for (int i=0; i<elements; ++i)
			{
				face = Subtitle_Regular;
				ePangoSubtitlePageElement &element = m_pango_page.m_elements[i];
				std::string text = element.m_pango_line;
				text = replace_all(text, "&apos;", "'");
				text = replace_all(text, "&quot;", "\"");
				text = replace_all(text, "&amp;", "&");
				text = replace_all(text, "&lt;", "<");
				text = replace_all(text, "&gt;", ">");

				std::string shadow_text = text;
				if (edgestyle == FONTSTYLE_RAISED || edgestyle == FONTSTYLE_DEPRESSED)
				{
					shadow_text = replace_all(shadow_text, "</u>", "");
					shadow_text = replace_all(shadow_text, "</i>", "");
					shadow_text = replace_all(shadow_text, "</b>", "");
					shadow_text = replace_all(shadow_text, "<u>", "");
					shadow_text = replace_all(shadow_text, "<i>", "");
					shadow_text = replace_all(shadow_text, "<b>", "");
				}

				if (ePythonConfigQuery::getConfigBoolValue("config.subtitles.pango_subtitle_fontswitch"))
				{
					if (text.find("<i>") != std::string::npos || text.find("</i>") != std::string::npos)
						face = Subtitle_Italic;
					else if (text.find("<b>") != std::string::npos || text.find("</b>") != std::string::npos)
						face = Subtitle_Bold;
				}
				int subtitleColors = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_fontcolor", 1);
				if (!subtitleColors)
					{
						text = replace_all(text, "<i>", gRGB(255,255,0));
						text = replace_all(text, "<b>", gRGB(0,255,255));
						text = replace_all(text, "<u>", (std::string) gRGB(0,255,0));
						text = replace_all(text, "</i>", (std::string) gRGB(255,255,255));
						text = replace_all(text, "</b>", (std::string) gRGB(255,255,255));
						text = replace_all(text, "</u>", (std::string) gRGB(255,255,255));
					}
				else
				{
					text = replace_all(text, "</u>", "");
					text = replace_all(text, "</i>", "");
					text = replace_all(text, "</b>", "");
					text = replace_all(text, "<u>", "");
					text = replace_all(text, "<i>", "");
					text = replace_all(text, "<b>", "");
				}

				gRGB fontcolor = (!subtitleStyles[face].have_foreground_color) ? element.m_color : subtitleStyles[face].foreground_color;
				switch (subtitleColors)
				{
					default:
					case 0: /* use original colors */
						original_colors = true;
						break;
					case FONTCOLOR_WHITE:
						fontcolor = gRGB(255, 255, 255);
						break;
					case FONTCOLOR_YELLOW:
						fontcolor = gRGB(255, 255, 0);
						break;
					case FONTCOLOR_GREEN:
						fontcolor = gRGB(0, 255, 0);
						break;
					case FONTCOLOR_CYAN:
						fontcolor = gRGB(0, 255, 255);
						break;
					case FONTCOLOR_BLUE:
						fontcolor = gRGB(0, 0, 255);
						break;
					case FONTCOLOR_MAGNETA:
						fontcolor = gRGB(255, 0, 255);
						break;
					case FONTCOLOR_RED:
						fontcolor = gRGB(255, 0, 0);
						break;
					case FONTCOLOR_BLACK:
						fontcolor = gRGB(0, 0, 0);
						break;
				}
				fontcolor.a = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_opacity");
				if (!original_colors)
					text = (std::string)fontcolor + text;

				subtitleStyles[face].font->pointSize = fontsize;
				painter.setFont(subtitleStyles[face].font);
				eRect &area = element.m_area;
				int bg_r, bg_g, bg_b, bg_a;
				if (ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_bgopacity") < 0xFF)
				{
					unsigned int padding = 10;
					eTextPara *para = new eTextPara(area);
					para->setFont(subtitleStyles[face].font);
					para->renderString(text.c_str(), RS_WRAP);

					eRect bgbox = para->getBoundBox();
					int bgboxWidth = bgbox.width();
					int bgboxHeight = bgbox.height();
					if (alignmentValue == "left")
						bgbox.setLeft(area.left() - padding - borderwidth);
					else if (alignmentValue == "right")
						bgbox.setLeft(area.left() + area.width() - bgboxWidth - padding - borderwidth);
					else
						bgbox.setLeft(area.left() + area.width() / 2 - bgboxWidth / 2 - padding - borderwidth);
					bgbox.setTop(area.top() + area.height() / 2 - bgboxHeight / 2 - padding * 2 - borderwidth);
					bgbox.setWidth(bgboxWidth + padding * 2 + borderwidth * 2);
					bgbox.setHeight(bgboxHeight + padding * 3 + borderwidth * 2);

					switch (ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_bgcolor", 0))
					{
						case BGCOLOR_WHITE:
							bg_r = 255;
							bg_g = 255;
							bg_b = 255;
							break;
						case BGCOLOR_YELLOW:
							bg_r = 255;
							bg_g = 255;
							bg_b = 0;
							break;
						case BGCOLOR_GREEN:
							bg_r = 0;
							bg_g = 255;
							bg_b = 0;
							break;
						case BGCOLOR_CYAN:
							bg_r = 0;
							bg_g = 255;
							bg_b = 255;
							break;
						case BGCOLOR_BLUE:
							bg_r = 0;
							bg_g = 0;
							bg_b = 255;
							break;
						case BGCOLOR_MAGNETA:
							bg_r = 255;
							bg_g = 0;
							bg_b = 255;
							break;
						case BGCOLOR_RED:
							bg_r = 255;
							bg_g = 0;
							bg_b = 0;
							break;
						case BGCOLOR_BLACK:
						default:
							bg_r = 0;
							bg_g = 0;
							bg_b = 0;
							break;
					}
					bg_a = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_bgopacity", 0);

					painter.setForegroundColor(gRGB(bg_r, bg_g, bg_b, bg_a));
					painter.fill(bgbox);
				}

				int offset = ePythonConfigQuery::getConfigIntValue("config.subtitles.subtitle_edgestyle_level", 3);
				switch(edgestyle)
				{
					default:
					case FONTSTYLE_NONE:
						offset = 0;
						borderwidth = 0;
						break;
					case FONTSTYLE_RAISED:
					{
						eRect shadow = area;
						ePoint shadow_offset = ePoint(-offset, -offset);
						shadow.moveBy(shadow_offset);
						painter.setForegroundColor(subtitleStyles[face].shadow_color);
						painter.renderText(shadow, shadow_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|rt_halignment_flag);
					}
						break;
					case FONTSTYLE_DEPRESSED:
					{
						eRect shadow = area;
						ePoint shadow_offset = ePoint(offset, offset);
						shadow.moveBy(shadow_offset);
						painter.setForegroundColor(subtitleStyles[face].shadow_color);
						painter.renderText(shadow, shadow_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|rt_halignment_flag);
					}
						break;
					case FONTSTYLE_UNIFORM:
					{
						if (borderwidth > 0)
						{
							if (fontcolor.r == 0 && fontcolor.g == 0 && fontcolor.b == 0)
							{
								gRGB tmp_border_white = gRGB(255,255,255);
								bordercolor = tmp_border_white;
							}
							else if (bg_r == 0 && bg_g == 0 && bg_b == 0)
							{
								borderwidth = 0;
							}
						}
					}
						break;
				}

				if ( !subtitleStyles[face].have_foreground_color && element.m_have_color )
					painter.setForegroundColor(element.m_color);
				else
					painter.setForegroundColor(subtitleStyles[face].foreground_color);
				painter.renderText(area, text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|rt_halignment_flag, bordercolor, borderwidth);
			}
		}
		else if (m_dvb_page_ok)
		{
			for (std::list<eDVBSubtitleRegion>::iterator it(m_dvb_page.m_regions.begin()); it != m_dvb_page.m_regions.end(); ++it)
			{
				eRect r = eRect(it->m_position, it->m_pixmap->size());
				r.scale(size().width(), m_dvb_page.m_display_size.width(), size().height(),  m_dvb_page.m_display_size.height());
				painter.blitScale(it->m_pixmap, r);
			}
		}
		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}

void eSubtitleWidget::setFontStyle(subfont_t face, gFont *font, int haveColor, const gRGB &col, const gRGB &shadowCol, const ePoint &shadowOffset)
{
	subtitleStyles[face].font = font;
	subtitleStyles[face].have_foreground_color = haveColor;
	subtitleStyles[face].foreground_color = col;
	subtitleStyles[face].shadow_color = shadowCol;
	subtitleStyles[face].shadow_offset = shadowOffset;
}

