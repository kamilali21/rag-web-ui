import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnalysisHistory } from "../analysis-history";
import { api, ApiError } from "@/lib/api";
jest.mock("@/lib/api", () => ({ ...jest.requireActual("@/lib/api"), api: { get: jest.fn(), post: jest.fn() } }));
const entry = (id=10) => ({ id, analysis_type:'summary',status:'complete',scope:'private',created_at:'2026-10-27T06:00:00',available:true,question:null,documents:[{id:1,title:'Water study'}] });
const saved = { id:10,analysis_type:'summary',status:'complete',result:{status:'complete',document:{id:1,scope:'private',knowledge_base_id:3,file_name:'water.pdf'},sections:[{key:'objective',title:'Objective',unavailable:false,claims:[{text:'Irrigation evidence.',citations:[{id:1,document_id:1,scope:'private',knowledge_base_id:3,file_name:'water.pdf',page:0}]}]}]}, evidence:[{evidence_id:'E1',document_id:1,page:0,excerpt:'<script>not HTML</script>',evidence_hash:'abc'}] };
beforeEach(() => { jest.clearAllMocks(); window.history.replaceState(null,'','/dashboard/insights/history');
  jest.mocked(api.get).mockImplementation(async url => url.includes('/history?') ? { items:[entry()],next_before_id:null } : saved); });

test('reopens summary and stored evidence without generating and restores keyboard focus', async () => {
  const user=userEvent.setup(); render(<AnalysisHistory />);
  const button=await screen.findByRole('button',{name:'Open summary 10'});
  await user.click(button);
  expect(await screen.findByText('Irrigation evidence.')).toBeInTheDocument();
  expect(screen.getByRole('link',{name:'Open water.pdf, page 1'})).toHaveAttribute('href','/api/knowledge-base/3/documents/1/content?inline=true#page=1');
  await user.click(screen.getByText('Saved evidence snapshots (1)'));
  expect(screen.getByText('<script>not HTML</script>').querySelector('script')).toBeNull();
  expect(api.post).not.toHaveBeenCalled();
  expect(window.location.search).toBe('?run=10');
  await user.keyboard('{Escape}');
  expect(window.location.search).toBe('');
  expect(button).toHaveFocus();
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

test('filters and stable cursor pages send bounded requests; reset when filter changes', async () => {
  jest.mocked(api.get).mockImplementation(async url => ({items:[entry(url.includes('before_id')?8:10)],next_before_id:url.includes('before_id')?null:10}));
  const user=userEvent.setup(); render(<AnalysisHistory />);
  await screen.findByRole('table',{name:'Saved research'});
  await user.click(screen.getByRole('button',{name:'Next history page'}));
  await screen.findByRole('button',{name:'Open summary 8'});
  expect(api.get).toHaveBeenCalledWith('/api/insights/history?limit=20&before_id=10',expect.anything());
  await user.selectOptions(screen.getByLabelText('Workflow'),'candidate_gaps');
  await waitFor(()=>expect(api.get).toHaveBeenCalledWith('/api/insights/history?limit=20&analysis_type=candidate_gaps',expect.anything()));
  expect(screen.getByText('Page 1')).toBeInTheDocument();
});

test('unavailable rows disclose no titles and cannot be opened', async () => {
  jest.mocked(api.get).mockResolvedValue({items:[{...entry(),available:false,documents:[],question:null}],next_before_id:null});
  render(<AnalysisHistory />);
  expect(await screen.findByText('Sources no longer available')).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Open summary 10'})).toBeDisabled();
  expect(screen.queryByText('Water study')).not.toBeInTheDocument();
});

test('deep link denial shows retry without stale result or regeneration', async () => {
  window.history.replaceState(null,'','/dashboard/insights/history?run=10');
  jest.mocked(api.get).mockImplementation(async url => { if (url.endsWith('/10')) throw new ApiError(404,'Sources unavailable'); return {items:[],next_before_id:null}; });
  render(<AnalysisHistory />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Sources unavailable');
  expect(screen.getByRole('button',{name:'Check saved result'})).toBeEnabled();
  expect(api.post).not.toHaveBeenCalled();
});

test('empty and failed list states allow retry', async () => {
  jest.mocked(api.get).mockRejectedValueOnce(new ApiError(503,'Temporarily unavailable')).mockResolvedValue({items:[],next_before_id:null});
  const user=userEvent.setup();render(<AnalysisHistory />);
  await user.click(await screen.findByRole('button',{name:'Retry history'}));
  expect(await screen.findByText('No saved research yet')).toBeInTheDocument();
});

test('failed and processing saved runs have explicit status and no generation action', async () => {
  window.history.replaceState(null,'','/dashboard/insights/history?run=10');
  jest.mocked(api.get).mockImplementation(async url => url.endsWith('/10') ? {...saved,status:'failed',error_message:'Provider busy',result:null,evidence:[]} : {items:[],next_before_id:null});
  render(<AnalysisHistory />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Provider busy');
  expect(api.post).not.toHaveBeenCalled();
});

test.each(['compare','analyze','contradictions','candidate_gaps'])('history renders saved %s using its existing result view', async kind => {
  window.history.replaceState(null,'','/dashboard/insights/history?run=10');
  const result = kind==='compare'
    ? {criteria:[],documents:[],compatibility:{label:'Related',explanation:'Saved comparability',citations:[]},notice:'Stored evidence only'}
    : {profiles:[],sections:[],documents:[],coverage:{selected_count:1,related_count:0,evidence_count:1,enabled:false},focus:kind,interpretations:[],candidate_gaps:[],notice:'Stored evidence only'};
  jest.mocked(api.get).mockImplementation(async url => url.endsWith('/10') ? {...saved,analysis_type:kind,result,evidence:[]} : {items:[],next_before_id:null});
  render(<AnalysisHistory />);
  expect(await screen.findByText('Stored evidence only')).toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});

test('processing status can be refreshed without another POST', async () => {
  window.history.replaceState(null,'','/dashboard/insights/history?run=10');
  jest.mocked(api.get).mockImplementation(async url => url.endsWith('/10') ? {...saved,status:'processing',result:null,evidence:[]} : {items:[],next_before_id:null});
  const user=userEvent.setup(); render(<AnalysisHistory />);
  await screen.findByText(/Still processing/);
  jest.mocked(api.get).mockImplementation(async url => url.endsWith('/10') ? saved : {items:[],next_before_id:null});
  await user.click(screen.getByRole('button',{name:'Check saved result'}));
  expect(await screen.findByText('Irrigation evidence.')).toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});
