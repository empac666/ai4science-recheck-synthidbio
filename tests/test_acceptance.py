"""Protocol-mandated adversarial acceptance cases, using no scientific inputs."""
import csv
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'analysis')
import path_a
import path_b
import functional as f
from resampling import paired_draws,publish_bootstrap,secondary_window
import numpy as np

class Acceptance(unittest.TestCase):
    def fixture(self,folder,conflict=False,collision=False):
        g=folder/'g.csv'
        header=['','Plate Target ID','subset_name','sample_id','Non-distortionary g-value','Distortionary g-value','unique_name','Plate Target ID']
        rows=[]; experiments=[]
        cats={'C':'non_watermark_0.1','WN':'watermark_0.5','WD':'watermark_0.1'}
        for target in ['VEGFA','PD-L1','SC2RBD']:
            ep=folder/(target+'.csv'); erows=[]
            for i,(setting,cat) in enumerate(cats.items()):
                name=' ID'+str(i)+' '
                # Same names in all targets, opposed detector columns, exact boundaries.
                wn='0.545' if setting=='WN' else '0.5446'
                wd='0.722' if setting=='WD' else '0.7216'
                rows.append([str(len(rows)),target,cat,'Backbone 0',wn,wd,name,target])
                for rep in ['1','2']:
                    erows.append([name,rep,'TRUE','1e-8',cat,'Backbone 0',target])
            with ep.open('w',newline='') as stream:
                w=csv.writer(stream); w.writerow(['name','replicate','binding','kd','Subset_Name','Backbone_ID ','Plate_Target_ID']); w.writerows(erows)
            experiments.append(('VEGF-A' if target=='VEGFA' else target,ep))
        if conflict: rows[0][-1]='PD-L1'
        if collision:
            extra=rows[0].copy(); extra[6]='ｉｄ０'; extra[4]='0.9'; rows.append(extra)
        with g.open('w',newline='') as stream:
            w=csv.writer(stream); w.writerow(header); w.writerows(rows)
        return g,experiments

    def test_duplicate_header_conflict_both_paths(self):
        with tempfile.TemporaryDirectory(dir='data/cache') as tmp:
            p,_=self.fixture(Path(tmp),conflict=True)
            with self.assertRaisesRegex(ValueError,'Conflicting'): path_a.read_table(p,'g')
            with self.assertRaisesRegex(ValueError,'conflict|Nonidentical'): path_b.read_raw(p,False)

    def test_normalization_collision_conflict_both_paths(self):
        with tempfile.TemporaryDirectory(dir='data/cache') as tmp:
            p,_=self.fixture(Path(tmp),collision=True)
            with self.assertRaisesRegex(ValueError,'Conflicting'): path_a.read_table(p,'g')
            with self.assertRaisesRegex(ValueError,'conflict|Nonidentical'): path_b.read_raw(p,False)

    def test_cross_target_replicate_denominators_and_threshold_dispatch(self):
        with tempfile.TemporaryDirectory(dir='data/cache') as tmp:
            g,e=self.fixture(Path(tmp))
            with patch.object(path_a,'GFILE',g),patch.object(path_a,'EXPERIMENTS',e),patch.object(path_b,'GFILE',g),patch.object(path_b,'EXPERIMENTS',e):
                a,_,_=path_a.run(); b=path_b.run()
            self.assertEqual(a['canonical'],b)
            self.assertEqual(len(b['formal_keys']),9)
            self.assertEqual([r['N'] for r in b['detection']],[1]*6+[3,3])
            self.assertTrue(all(r['K']==r['N'] and r['equal']==r['N'] for r in b['detection']))
            for r in b['sensitivity']:
                self.assertEqual(r['K'],1 if r['variant']=='minus_0.0005' else 0)
                self.assertEqual(r['changed'],0 if r['variant']=='minus_0.0005' else 1)

    def test_units_numeric_and_missing(self):
        self.assertEqual(f.parse_kd('15.4')['value_mol_L'],'15.4')
        for s in ['15.4 nM','０．０１５４ uM','0.0154 µM','0.0154 μM']:
            self.assertEqual(Decimal(f.parse_kd(s)['value_mol_L']),Decimal('1.54e-8'))
        self.assertEqual(f.parse_kd('15.4', 'nM')['unit_source'],'header')
        self.assertEqual(f.parse_kd('15.4 nM','M')['reason'],'unit_conflict')
        for s in ['','NA','n/a','null','NaN']:
            self.assertEqual(f.parse_kd(s)['status'],'missing')
        for s in ['0','-1','inf','1,000','1 to 2','1e-8 xyz','>0','nan M']:
            self.assertEqual(f.parse_kd(s)['status'],'conflict')
        with self.assertRaises(ValueError): f.header_unit(['kd','kd (nM)'])

    def test_censoring_never_enters_mean(self):
        for op in ['>','>=','≥','<','<=','≤']:
            p=f.parse_kd(op+'1e-5'); self.assertEqual(p['status'],'censored')
            rows=[{'replicate':str(i),'binding_status':'TRUE','kd_parse':p} for i in [1,2]]
            d=f.summarize_design(rows)
            self.assertIsNone(d['kd_mean_mol_L'])
            self.assertTrue(d['nonquantifiable'])
            self.assertEqual(set(d['states'].values()),{'unknown'})

    def test_functional_flags_and_bounds(self):
        def design(bs,kds):
            return f.summarize_design([{'replicate':str(i),'binding_status':f.binding(b),'kd_parse':f.parse_kd(k)} for i,(b,k) in enumerate(zip(bs,kds))])
        clear=design(['TRUE','TRUE'],['5e-8','1.5e-7'])
        self.assertEqual(clear['states']['1e-7'],'hit')
        no=design(['FALSE','FALSE'],['null','NA'])
        self.assertEqual(no['states']['1e-7'],'nonhit')
        bad=design(['FALSE','FALSE'],['1e-8','null'])
        self.assertTrue(bad['conflict']); self.assertEqual(bad['states']['1e-7'],'unknown')
        mixed=design(['TRUE','FALSE'],['null','null'])
        self.assertTrue(mixed['mixed'])
        one=design(['TRUE'],['1e-8']); self.assertEqual(one['states']['1e-7'],'unknown')
        summary=f.cell([clear,no,bad,mixed,one],'1e-7')
        self.assertEqual((summary['n'],summary['a'],summary['u']),(5,1,3))
        self.assertEqual((summary['lower_bound'],summary['upper_bound']),(.2,.8))

    def test_resampling_pairing_and_cutoff(self):
        indices=np.tile(np.arange(15,dtype=np.int64),(10000,3,1))
        delta=np.arange(45).reshape(3,15)
        self.assertTrue(np.all(paired_draws(delta,indices)==22))
        rows=[{'iterations':10000}]*4
        self.assertEqual(publish_bootstrap(rows,True,74.9)['status'],'complete')
        for result in [publish_bootstrap(rows,True,75),publish_bootstrap(rows[:3],True,74),publish_bootstrap(rows,False,74)]:
            self.assertEqual(result['comparisons'],[])
        self.assertFalse(secondary_window(74.99)); self.assertTrue(secondary_window(75)); self.assertFalse(secondary_window(80))

if __name__=='__main__': unittest.main()
