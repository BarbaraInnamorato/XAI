import shap
import lime
import lime.lime_tabular
from lime import submodular_pick

from anchor import anchor_tabular
import matplotlib.pyplot as plt
import numpy as np
from numpyencoder import NumpyEncoder

import pandas as pd
import json
import time

from collections import defaultdict


# Connect pandas with plotly
import cufflinks as cf
cf.go_offline()
from plotly.offline import init_notebook_mode
init_notebook_mode(connected='true')


first_time = time.time() # returns the processor time

def d3_xai(data_for_xai, cols, all_cols, filename):
    '''
    Function for xai methods with D3 approach

    cols : swapped columns
    all_cols : all columns
    '''

    ret = []
    ret.append({'swapped columns': cols})
    ret.append({'columns': all_cols})

    lime_res = []
    lime_res.append({'swapped columns': cols})
    lime_res.append({'columns': all_cols})

    anchor_res = []
    anchor_res.append({'swapped columns': cols})
    anchor_res.append({'columns': all_cols})

    time_shap = []

    for diz in data_for_xai[-1:]:
        train_set = pd.DataFrame(diz['X_train'], columns=all_cols)
        test_set = pd.DataFrame(diz['X_test'], columns=all_cols)

        class_names = np.unique(diz['y_train'])

        k = 0

        print("D3 train accuracy: %0.3f" % diz['model'].score(train_set, diz['y_train']))
        print("D3 test accuracy: %0.3f" % diz['model'].score(test_set, diz['y_test']))


        # Setting explainers
        explainer_shap = shap.KernelExplainer(diz['model'].predict_proba,
                                              train_set,
                                              nsamples=100,
                                              random_state=90,
                                              link='identity',
                                              l1_reg=len(all_cols)
                                              )

        explainer_lime = lime.lime_tabular.LimeTabularExplainer(diz['X_train'],
                                                                mode='classification',
                                                                feature_names=all_cols,
                                                                feature_selection='none',
                                                                discretize_continuous=True,
                                                                discretizer='quartile',
                                                                verbose=True)

        explainer_anchor = anchor_tabular.AnchorTabularExplainer(class_names=class_names,
                                                                 feature_names=all_cols,
                                                                 train_data = diz['X_train'],
                                                                 #discretizer='quartile'
                                                                )

        # Start explanations

        for i in range(len(diz['X_test'])):  # da 0 a 66-1
            pred = diz['predictions'][i]
            predict_proba = diz['model'].predict_proba(diz['X_test'][i].reshape(1, -1))[0]


            #############################  SHAP  ##############################
            '''
            - le variabili con shap value negativo dovrebbero essere quelle che spingono verso zero 
            - feat_shap_val: le variabili sono ordinate in base al valore assoluto del rispettivo shap value
            - più lo shap_value in valore è assoluto è alto, più la variabile è importante 
            # mean = sum(abs(tup[0]) for tup in ordered_shap_list)/len(ordered_shap_list)
            '''
            start_time_sh = time.time()
            shap_values = explainer_shap.shap_values(test_set.iloc[i, :])
            time_shap1 = f"D3 - SHAP - Total time {filename}: {(time.time() - start_time_sh) / 60} minutes"

            # print(f"D3 - SHAP - Total time {filename}: {(time.time() - start_time) / 60} minutes")
            time_shap.append({'start':start_time_sh, 'end':time_shap1, 'iter':i})
            model_output = (explainer_shap.expected_value + shap_values[pred].sum()).round(4) #list of probs
            class_pred = np.argmax(abs(model_output))

            # questo mo_output è l'output della black-box
            #mo_output = (explainer_shap.expected_value[class_pred] + shap_values[class_pred].sum()).round(4)
            #print('mo output', mo_output)
            zipped = list(zip(shap_values[pred], all_cols))
            ordered_shap_list = sorted(zipped, key=lambda x: x[0], reverse=True)

            # Get the force plot for each row
            shap.initjs()
            shap.plots.force(explainer_shap.expected_value[class_pred], shap_values[class_pred],test_set.iloc[i,:], feature_names=all_cols, show=False, matplotlib = True, text_rotation=6)#, figsize=(50,12))
            #plt.title(f'Local forceplot row {str(i)} dataset {filename}', position=(0.3, 0.7))
            plt.tight_layout()
            plt.savefig('images/'+ f'D3 Local SHAP row {str(i)} dataset {filename}')


            swap_shap = [(tup[1], True if tup[1] in cols else False) for tup in ordered_shap_list]
            feat_shap_val = [(tup[1], round(tup[0], 3)) for tup in ordered_shap_list]

            dizio = {'batch %s' % k: {'row %s' % i: {
                'class_names': class_names,
                'd3_prediction': pred,                                          # D3 class predicted
                'd3_pred_probs': predict_proba,                                 # D3 probs predicted
                'SHAP_probs': model_output,
                'is ML correct': class_pred == pred,
                'value_ordered': feat_shap_val,                                 # (feature, shap_value) : ordered list
                'swapped': swap_shap,                                           # (feature, bool) : ordered list of swapped variables
                'shap_prediction': class_pred,                                  # xai prediction : class
                'shap_values': shap_values
            }}}
            ret.append(dizio)


            #############################  LIME  ###########################
            '''
            - le variabili con |weight| sono quelle più determinati per la prediction del ML model
            - feature_weight_sorted: le variabili sono ordinate in base al valore assoluto del rispettivo peso calcolato con lime
            - feature_value: valore reale del feature nella riga considerata
            # mean = round(sum(abs(tup[1]) for tup in big_lime_list)/len(big_lime_list),3)
            '''
            start_time_lime = time.time()
            exp_lime = explainer_lime.explain_instance(diz['X_test'][i],
                                                       diz['model'].predict_proba,
                                                       num_samples= 100,
                                                       distance_metric='euclidean')  # provare anche una distanza diversa

            ###
            time_lime1 = f"D3 - LIME - Total time: {(time.time() - start_time_lime) / 60} minutes"
            with open('other_files/' + f"D3 - LIME - Total time {filename}", 'w', encoding='utf-8') as t2:
                json.dump(time_lime1, t2, cls=NumpyEncoder)
            #print(f"D3 - LIME - Total time: {(time.time() - start_time) / 60} minutes")

            big_lime_list = exp_lime.as_list()  # list of tuples (representation, weight),
            ord_lime = sorted(big_lime_list, key=lambda x: abs(x[1]), reverse=True)

            lime_prediction = exp_lime.local_pred
            lime_class_pred = [0 if lime_prediction < 0.5 else 1][0]
            exp_lime.as_pyplot_figure().tight_layout()
            plt.text( 0.3, 0.7,f' D3 Local LIME row {str(i)}')
            #plt.subtitle(f' D3 Local LIME row {str(i)}', y=1.05, fontsize=18)
            plt.savefig('images/' +f' D3 Local LIME row {str(i)} dataset {filename}')

            #exp_lime.save_to_file(f'lime_row_{str(i)}.html') #OPTIONAL

            variables = []  # (name, real value)
            f_weight = []  # (feature, weight)
            swap = []  # (feature, bool)

            for t in ord_lime:
                tt = t[0].split(' ')
                if len(tt) == 3:
                    f_weight.append((tt[0], round(t[1], 3)))

                    if tt[0] in cols:
                        swap.append((tt[0], True))
                    else:
                        swap.append((tt[0], False))

                    variables.append((tt[0], round(float(tt[-1]), 3)))

                elif len(tt) > 3:
                    f_weight.append((tt[2], round(t[1], 3)))

                    if tt[2] in cols:
                        swap.append((tt[2], True))
                    else:
                        swap.append((tt[2], False))

                    mean_sum = round((float(tt[0]) + float(tt[-1])) / 2, 3)  # caso in cui il valore di un feature è in un range di valori
                    variables.append((tt[2], mean_sum))

            lime_diz = {'batch %s' % k: {'row %s' % i: {
                'class_names': class_names,
                'd3_prediction': pred,                                  # D3 prediction (LR)
                'd3_pred_probs': predict_proba,                         # D3 prediction (LR)
                'LIME_prediction': lime_class_pred,                     # xai prediction
                'LIME_LOCAL_prediction': lime_prediction,           # xai prediction
               # 'LIME_pred_probs': lime_probs,
                'value_ordered': f_weight,                              # (feature, lime_weight)
                'feature_value': variables,                             # (feature, real value)
                'swapped': swap                                         # (feature, bool)
            }}}

            lime_res.append(lime_diz)

            # SUBMODULAR PICk
            """
            There are two charts where we have aggregated the explanations across the 500 points we sampled from out test set(we can run it on
            all test data points, but chose to do sampling only cause of computation).

            The first chart aggregates the effect of the feature across 0 and 1 cases and ignores the sign when calculating the mean. 
            This gives you an idea of what features were important in the larger sense.

            The second chart splits the inference across the two labels and looks at them separately. This chart lets us understand 
            which feature was more important in predicting a particular class.
            """
            """
            print('SUBMODULAR PICK')


            # https://github.com/marcotcr/lime/blob/master/lime/submodular_pick.py
            sp_obj = submodular_pick.SubmodularPick(data=diz['X_train'],
                                                    explainer=explainer_lime,
                                                    num_features=len(all_cols),
                                                    predict_fn=diz['model'].predict_proba,
                                                    #num_exps_desired=10,
                                                    sample_size=20,
                                                    top_labels=len(class_names)
                                                    )
            # Plot the 10 explanations
            #[exp.as_pyplot_figure().savefig('images/'+ f'pl {filename}').tight_layout() for exp in sp_obj.sp_explanations]


            #sp_explanations: A list of explanation objects that has a high coverage
            #explanations: All the candidate explanations saved for potential future use.
            #to compute LIME COVERAGE: len(sp_obj.sp_explanations) / len(sp_obj.explanations)
            
            df=pd.DataFrame({})
            for this_label in range(len(class_names)):
                print('this_label', this_label)
                dfl=[]
                for i,exp in enumerate(sp_obj.sp_explanations):
                    exp.as_pyplot_figure().savefig(f'LIME global for {filename} {str(i)}');
                    l=exp.as_list(label=this_label)
                    l.append(("exp number",i))
                    dfl.append(dict(l))
                    print('dfl', dfl)
                #dftest=pd.DataFrame(dfl)
                df=df.append(pd.DataFrame(dfl,index=[class_names[this_label] for i in range(len(sp_obj.sp_explanations))]))
            print('SUBMODULAR PICK', df.head())
            """

            #############################  ANCHORS  ###########################
            '''
             An anchor is a sufficient condition - that is, when the anchor holds, the prediction should be the same as the prediction for this instance.

              explainer.explain_instance:
            - threshold: the previously discussed minimal confidence level. threshold defines the minimum fraction of samples for a candidate anchor that need to 
                  lead to the same prediction as the original instance. A higher value gives more confidence in the anchor, but also leads to more computation time. 
                  The default value is 0.95.
            - tau: determines when we assume convergence for the multi-armed bandit. A bigger value for tau means faster convergence but also looser anchor conditions.
                  By default equal to 0.15.
            - beam_size: the size of the beam width. A bigger beam width can lead to a better overall anchor at the expense of more computation time.
            - batch_size: the batch size used for sampling. A bigger batch size gives more confidence in the anchor, again at the expense of computation time since
                  it involves more model prediction calls. The default value is 100.
            - coverage_samples: number of samples used to compute the coverage of the anchor. By default set to 10000.

            We set the precision threshold to 0.95. This means that predictions on observations where the anchor holds will be the same as the prediction on 
            the explained instance at least 95% of the time.

            https://github.com/marcotcr/anchor/blob/master/notebooks/Anchor%20on%20tabular%20data.ipynb
            '''

            start_time_anchor = time.time()
            exp_anchor = explainer_anchor.explain_instance(diz['X_test'][i],
                                                           diz['model'].predict,
                                                           threshold=0.90,
                                                           beam_size=len(all_cols))
            #print(f"D3 -ANCHOR - Total time: {(time.time() - start_time) / 60} minutes")
            time_anchor1 = f"D3 -ANCHOR - Total time: {(time.time() - start_time_anchor) / 60} minutes"
            with open('other_files/' + f"D3 - ANCHOR - Total time {filename}", 'w', encoding='utf-8') as t3:
                json.dump(time_anchor1, t3, cls=NumpyEncoder)

            prediction = explainer_anchor.class_names[diz['model'].predict(diz['X_test'][i].reshape(1, -1))[0]]

            # exp_anchor.show_in_notebook()
            # exp_anchor.examples(only_different_prediction = True)
            # print('esempi',exp_anchor.examples()) #np.ndarray

            rules = exp_anchor.names()
            precision = round(exp_anchor.precision(), 3)
            coverage = round(exp_anchor.coverage(), 3)

            '''
            print()
            print('anchor: %s' % (' AND '.join(exp_anchor.names())))
            print('precision: %.2f' % exp_anchor.precision())
            print('coverage: %.2f' % exp_anchor.coverage())

            # Get test examples where the anchora applies
            fit_anchor = np.where(np.all(diz['X_test'][i:, exp_anchor.features()] == diz['X_test'][i][exp_anchor.features()], axis=1))[0]
            print('Anchor test precision: %.2f' % (np.mean(diz['model'].predict(diz['X_test'][fit_anchor]) == diz['model'].predict(diz['X_test'][i].reshape(1, -1)))))
            print('Anchor test coverage: %.2f' % (fit_anchor.shape[0] / float(test_set.shape[0])))    
            print()'''

            contrib = []
            swapped = []

            if len(rules) == 0:
                if len(contrib) > 0:
                    contrib.append(contrib[-1])
                else:
                    contrib.append(
                        'empty rule: all neighbors have the same label')  # al primo batch potrebbe essere vuoto


            else:
                for s in rules:  # nel caso in cui ci siano più predicati

                    splittato = s.split(' ')  # splittato = [nswprice, >, 0.08], [0.3 <= feature <= 0.6]
                    n = len(splittato)

                    if n == 3:  # 1 feature: caso tipo [feature <= 0.5]
                        contrib.append(splittato[0])
                        if splittato[0] in cols:
                            swapped.append((splittato[0], True))
                        else:
                            swapped.append((splittato[0], False))
                    if n > 3:  # more than 1 feature: caso tipo rules = ['nswprice > 0.08', 'vicprice > 0.00', 'day <= 2.00']
                        # pos = 0                                      # splittato = [nswprice, >, 0.08]
                        for el in splittato:
                            if el.isalpha() and el in cols:
                                contrib.append(el)
                                swapped.append((el, True))

                            elif el.isalpha() and not el in cols:
                                contrib.append(el)
                                swapped.append((el, False))

                            else:  # caso tipo: 0.3 <= feature <= 0.6
                                pos = 2
                                # print('splittato',splittato)
                                contrib.append(splittato[pos])
                                if splittato[pos] in cols:
                                    swapped.append((splittato[pos], True))
                                    break
                                else:
                                    swapped.append((splittato[pos], False))
                                    break

            diz_anchors = {'batch %s' % k: {'row %s' % i: {
                'class_names': class_names,
                'd3_prediction': pred,
                'd3_pred_probs': predict_proba,
                'Anchor_prediction': prediction,
                'rule': ' AND '.join(exp_anchor.names()),
                'precision': precision,
                'coverage': coverage,
                'swapped': swapped,
                'value_ordered': contrib,
            }}}

            anchor_res.append(diz_anchors)

        k += 1

    # print()
    # print('D3 ANCHORS')
    # print(anchor_res)

    print('LIME')
    print(lime_res)

    # D3 FILES
    with open('results/' + 'D3_SHAP_%s.json' % filename, 'w', encoding='utf-8') as f:
        json.dump(ret, f, cls=NumpyEncoder)

    with open('results/' + 'D3_LIME_%s.json' % filename, 'w', encoding='utf-8') as f1:
        json.dump(lime_res, f1, cls=NumpyEncoder)

    with open('other_files/' + 'D3_ANCHORS_%s.json' % filename, 'w', encoding='utf-8') as ff2:
    #with open('results/' + 'D3_ANCHORS_%s.json' % filename, 'w', encoding='utf-8') as ff2:
        json.dump(anchor_res, ff2, cls=NumpyEncoder)

    with open('other_files/' + f"D3 - SHAP - Total time {filename}", 'w', encoding='utf-8') as t1:
        json.dump(time_shap, t1, cls=NumpyEncoder)
    #return ret, anchor_res, lime_res

    f.close()
    f1.close()
    ff2.close()
    t1.close()
    t2.close()
    t3.close()



def st_xai(data_for_xai, cols, all_cols, filename):
    '''
        Function for xai methods with student-teacher approach

    cols : swapped columns
    all_cols : all columns
    '''
    k = 0
    ret_st = []
    ret_st.append({'swapped columns': cols})
    ret_st.append({'columns': all_cols})

    lime_res_st = []
    lime_res_st.append({'swapped columns': cols})
    lime_res_st.append({'columns': all_cols})

    anchor_res_st = []
    anchor_res_st.append({'swapped columns': cols})
    anchor_res_st.append({'columns': all_cols})

    for diz in data_for_xai:
        print('---- ST ------')
        train_set = pd.DataFrame(diz['X_train'], columns=all_cols)
        test_set = pd.DataFrame(diz['X_test'], columns=all_cols)

        class_names = np.unique(diz['y_train'])

        explainer_shap = shap.KernelExplainer(diz['model'].predict_proba,
                                              train_set,
                                              nsamples=100,
                                              random_state=90,
                                              link='identity',
                                              l1_reg = len(all_cols)
                                              )


        explainer_lime = lime.lime_tabular.LimeTabularExplainer(diz['X_train'],
                                                                mode='classification',
                                                                feature_names=all_cols,
                                                                feature_selection='none',
                                                                discretize_continuous=True,
                                                                discretizer='quartile',
                                                                verbose=False)

        explainer_anchor = anchor_tabular.AnchorTabularExplainer(class_names = class_names,
                                                                 feature_names=all_cols,
                                                                 train_data=diz['X_train'],
                                                                 #discretizer='quartile'
                                                                )


        pred = int(diz['class_student'])
        predict_proba = diz['model'].predict_proba(diz['X_test'][0].reshape(1, -1))[0]  # default: l2 penalty = ridge regression

        #############################  SHAP  ##############################
        '''
        - le variabili con shap value negativo dovrebbero essere quelle che spingono verso zero 
        - feat_shap_val: le variabili sono ordinate in base al valore assoluto del rispettivo shap value
        - più lo shap_value in valore è assoluto è alto, più la variabile è importante 
        - #mean = sum(abs(tup[0]) for tup in ordered_shap_list)/len(ordered_shap_list)

        '''
        start_time = time.time()
        shap_values = explainer_shap.shap_values(test_set) # test set è una riga
        #print(f"-ST -SHAP Total time {filename}: {(time.time() - start_time) / 60} minutes")
        time_shap2 = f"-ST -SHAP Total time {filename}: {(time.time() - start_time) / 60} minutes"
        with open('other_files/' + f"ST - SHAP - Total time {filename}", 'w', encoding='utf-8') as t4:
            json.dump(time_shap2, t4, cls=NumpyEncoder)

        #expected_values = list(explainer_shap.expected_value)
        print(f'ST shap values {filename}', shap_values)
        print(f'ST expected values {filename}', explainer_shap.expected_value)

        model_output = (explainer_shap.expected_value + shap_values[pred].sum()).round(4)
        class_pred = np.argmax(abs(model_output))

        zipped = list(zip(shap_values[class_pred][0], all_cols))
        ordered_shap_list = sorted(zipped, key=lambda x: x[0], reverse=True)


        # Get the force plot for each row
        shap.initjs()
        shap.plots.force(explainer_shap.expected_value[class_pred], shap_values[class_pred], test_set , feature_names=all_cols, show=False, matplotlib = True, text_rotation=6)#, figsize=(50,12))
        #plt.title('Local Force plot row %s'%k)
        name = f'ST Local Force plot row {str(k)}, dataset {filename}'
        plt.tight_layout()
        plt.savefig('images/'+ name)

        swap_shap = [(tup[1], True if tup[1] in cols else False) for tup in ordered_shap_list]
        feat_shap_val = [(tup[1], tup[0]) for tup in ordered_shap_list]
        #model_output = (explainer_shap.expected_value[pred] + shap_values[0].sum()).round(4)

        dizio = {'batch %s' % k: {'row %s' % k: {
            'class_names': class_names,
            'ST_prediction': pred,
            'ST_pred_probs': predict_proba,             # ST prediction
            'is ML correct': class_pred == pred,
            'SHAP_prediction': class_pred,
            'value_ordered': feat_shap_val,        # (feature, shap_value)
            'swapped': swap_shap,                       # (feature, bool),
            'SHAP_probs': model_output,            # xai prediction
            'shap_values' : shap_values
        }}}
        ret_st.append(dizio)

        ############################### LIME ################################
        start_time = time.time()
        exp_lime = explainer_lime.explain_instance(diz['X_test'][0],
                                                   diz['model'].predict_proba,
                                                   num_samples=100,
                                                   distance_metric='euclidean') # provare anche una distanza diversa
        print('%s -ST - LIME' % filename)
        #print(f"Total time: {(time.time() - start_time) / 60} minutes")
        time_lime2 = f"Total time: {(time.time() - start_time) / 60} minutes"
        with open('other_files/' + f"ST - LIME - Total time {filename}", 'w', encoding='utf-8') as t5:
            json.dump(time_lime2, t5, cls=NumpyEncoder)

        #lime_probs = list(exp_lime.predict_proba)  # prob of being in class 0 or in class 1
        big_lime_list = exp_lime.as_list()  # list of tuples (representation, weight),
        ord_lime = sorted(big_lime_list, key=lambda x: abs(x[1]), reverse=True)
        lime_prediction = exp_lime.local_pred
        lime_class_pred = [0 if lime_prediction < 0.5 else 1][0]
        exp_lime.as_pyplot_figure().tight_layout()
        plt.text(0.3, 0.7, f' D3 Local LIME row {str(k)}')
        plt.savefig('images/' + f' ST Local LIME row {str(k)} dataset {filename}')

        variables = []  # (name, real value)
        f_weight = []  # (feature, weight)
        swap = []  # (feature, bool)

        for t in ord_lime:
            tt = t[0].split(' ')
            if len(tt) == 3:
                f_weight.append((tt[0], round(t[1], 3)))

                if tt[0] in cols:
                    swap.append((tt[0], True))
                else:
                    swap.append((tt[0], False))

                variables.append((tt[0], round(float(tt[-1]), 3)))

            elif len(tt) > 3:
                f_weight.append((tt[2], round(t[1], 3)))

                if tt[2] in cols:
                    swap.append((tt[2], True))
                else:
                    swap.append((tt[2], False))

                mean_sum = round((float(tt[0]) + float(tt[-1])) / 2,
                                 3)  # caso in cui il valore di un feature è in un range di valori
                variables.append((tt[2], mean_sum))

        lime_diz = {'batch %s' % k: {'row %s' % k: {
            'class_names': class_names,
            'ST_prediction': pred,                              # ST prediction
            'ST_pred_probs': predict_proba,                     # ST predicted probs
            'LIME_LOCAL_prediction': lime_prediction,       # xai prediction
            'LIME_prediction': lime_class_pred,                 # xai prediction
            'value_ordered': f_weight,                          # (feature, lime_weight)
            'feature_value': variables,                         # (feature, real value)
            'swapped': swap                                     # (feature, bool)

        }}}

        lime_res_st.append(lime_diz)

        # SUBMODULAR PICk
        """
        There are two charts where we have aggregated the explanations across the 500 points we sampled from out test set(we can run it on
        all test data points, but chose to do sampling only cause of computation).
        
        The first chart aggregates the effect of the feature across 0 and 1 cases and ignores the sign when calculating the mean. 
        This gives you an idea of what features were important in the larger sense.

        The second chart splits the inference across the two labels and looks at them separately. This chart lets us understand 
        which feature was more important in predicting a particular class.
        """
        """
        sp_obj = submodular_pick.SubmodularPick(explainer_lime,
                                                diz['X_train'],
                                                diz['model'].predict_proba,
                                                sample_size=200,
                                                num_features=len(all_cols),
                                                num_exps_desired=10)
        # Plot the 5 explanations
        [exp_lime.as_pyplot_figure(label=exp_lime.available_labels()[0]) for exp_lime in sp_obj.sp_explanations]
        # Make it into a dataframe
        W_pick = pd.DataFrame(
            [dict(this.as_list(this.available_labels()[0])) for this in sp_obj.sp_explanations]).fillna(0)

        W_pick['prediction'] = [this.available_labels()[0] for this in sp_obj.sp_explanations]

        # Making a dataframe of all the explanations of sampled points
        W = pd.DataFrame([dict(this.as_list(this.available_labels()[0])) for this in sp_obj.explanations]).fillna(0)
        W['prediction'] = [this.available_labels()[0] for this in sp_obj.explanations]

        # Plotting the aggregate importances
        np.abs(W.drop("prediction", axis=1)).mean(axis=0).sort_values(ascending=False).head(5).sort_values(ascending=True).py.plot(kind="barh")

        # Aggregate importances split by classes
        grped_coeff = W.groupby("prediction").mean()

        grped_coeff = grped_coeff.T
        grped_coeff["abs"] = np.abs(grped_coeff.iloc[:, 0])
        grped_coeff.sort_values("abs", inplace=True, ascending=False)
        grped_coeff.head(25).sort_values("abs", ascending=True).drop("abs", axis=1).py.plot(
            kind="barh", bargap=0.5)"""

        ################### ANCHORS #########################################
        start_time = time.time()
        exp_anchor = explainer_anchor.explain_instance(diz['X_test'][0],
                                                       diz['model'].predict,
                                                       threshold=0.90,
                                                       beam_size=len(all_cols))


        #print(f"Total time: {(time.time() - start_time) / 60} minutes")
        time_anchor2 = f"Total time: {(time.time() - start_time) / 60} minutes"
        with open('other_files/' + f"ST - ANCHOR - Total time {filename}", 'w', encoding='utf-8') as t6:
            json.dump(time_anchor2, t6, cls=NumpyEncoder)

        prediction_anch = explainer_anchor.class_names[diz['model'].predict(diz['X_test'].reshape(1, -1))[0]]

        # exp_anchor.show_in_notebook()
        # exp_anchor.examples(only_different_prediction = True)
        # print('esempi',exp_anchor.examples()) #np.ndarray

        rules = exp_anchor.names()
        precision = round(exp_anchor.precision(), 3)
        coverage = round(exp_anchor.coverage(), 3)

        '''
        print()
        print('anchor: %s' % (' AND '.join(exp_anchor.names())))
        print('precision: %.2f' % exp_anchor.precision())
        print('coverage: %.2f' % exp_anchor.coverage())

        # Get test examples where the anchora applies
        fit_anchor = np.where(np.all(diz['X_test'][i:, exp_anchor.features()] == diz['X_test'][i][exp_anchor.features()], axis=1))[0]
        print('Anchor test precision: %.2f' % (np.mean(diz['model'].predict(diz['X_test'][fit_anchor]) == diz['model'].predict(diz['X_test'][i].reshape(1, -1)))))
        print('Anchor test coverage: %.2f' % (fit_anchor.shape[0] / float(test_set.shape[0])))    
        print()'''

        contrib = []
        swapped = []

        if len(rules) == 0:
            if len(contrib) > 0:
                contrib.append(contrib[-1])
            else:
                contrib.append('empty rule: all neighbors have the same label')  # al primo batch potrebbe essere vuoto


        else:
            for s in rules:  # nel caso in cui ci siano più predicati
                splittato = s.split(' ')  # splittato = [nswprice, >, 0.08], [0.3 <= feature <= 0.6]
                # print('split', splittato)
                n = len(splittato)

                if n == 3:  # 1 feature: caso tipo [feature <= 0.5]
                    contrib.append(splittato[0])
                    if splittato[0] in cols:
                        swapped.append((splittato[0], True))
                    else:
                        swapped.append((splittato[0], False))
                if n > 3:  # more than 1 feature: caso tipo rules = ['nswprice > 0.08', 'vicprice > 0.00', 'day <= 2.00']
                    # pos = 0                                      # splittato = [nswprice, >, 0.08]
                    for el in splittato:
                        if el.isalpha() and el in cols:
                            contrib.append(el)
                            swapped.append((el, True))

                        elif el.isalpha() and not el in cols:
                            contrib.append(el)
                            swapped.append((el, False))

                        else:  # caso tipo: 0.3 <= feature <= 0.6
                            pos = 2
                            # print('splittato',splittato)
                            contrib.append(splittato[pos])
                            if splittato[pos] in cols:
                                swapped.append((splittato[pos], True))
                                break
                            else:
                                swapped.append((splittato[pos], False))
                                break

        diz_anchors = {'batch %s' % k: {'row %s' % k: {
            'class_names': class_names,
            'ML_prediction': pred,                       # ST prediction
            'ML_pred_probs': predict_proba,              # ST predicted proba
            'Anchor_prediction': prediction_anch,        # xai prediction
            'rule': ' AND '.join(exp_anchor.names()),    # anchor
            'precision': precision,
            'coverage': coverage,
            'swapped': swapped,                          # (feature, bool)
            'value_ordered': contrib,               # list of features
        }}}

        anchor_res_st.append(diz_anchors)

        k += 1




    # ST FILES
    with open('results/' + 'ST_SHAP_%s.json' % filename, 'w', encoding='utf-8') as f:
        json.dump(ret_st, f, cls=NumpyEncoder)

    with open('results/' + 'ST_LIME_%s.json' % filename, 'w', encoding='utf-8') as f1:
        json.dump(lime_res_st, f1, cls=NumpyEncoder)

    with open('other_files/' + 'ST_ANCHORS_%s.json' % filename, 'w', encoding='utf-8') as f2:
    #with open('results/' + 'ST_ANCHORS_%s.json' % filename, 'w', encoding='utf-8') as f2:
        json.dump(anchor_res_st, f2, cls=NumpyEncoder)

    f.close()
    f1.close()
    f2.close()
    t4.close()
    t5.close()
    t6.close()

    #return ret, lime_res, anchor_res


tot_time = f"XAI.PY Total time: {(time.time() - first_time) / 60} minutes"
# with open('other_files/' + f"XAI - Total time", 'w', encoding='utf-8') as t7:
#     json.dump(tot_time, t7, cls=NumpyEncoder)
print(f"XAI.PY Total time: {(time.time() - first_time) / 60} minutes")
print('END XAI')


"""
from pycebox.ice import ice, ice_plot
def ice_plot(data_for_xai, cols, all_cols):
"""