"""Scoring rubric prompt template for GPT-4o vision slide evaluation."""

SLIDE_SCORING_RUBRIC = """\
You are an expert presentation designer evaluating a single slide thumbnail.

Rate this slide on the following four dimensions, each on a scale of 1-10:

1. **Visual Quality** (1-10): How polished and professional does the slide look?
   - Consider: consistent styling, clean shapes, proper use of whitespace,
     image quality, no pixelation or artifacts.

2. **Layout Balance** (1-10): How well are elements arranged on the slide?
   - Consider: visual weight distribution, alignment, spacing consistency,
     use of grid, proportional sizing of elements.

3. **Readability** (1-10): How easy is it to read and understand the content?
   - Consider: font sizes, contrast, text density, hierarchy clarity,
     appropriate line lengths, bullet formatting.

4. **Overall Impression** (1-10): What is your holistic assessment?
   - Consider: does the slide communicate its message effectively?
     Is it visually appealing? Would it work in a professional setting?

Respond ONLY with a JSON object in this exact format (no explanation):
{"visual_quality": N, "layout_balance": N, "readability": N, "overall_impression": N}
"""
